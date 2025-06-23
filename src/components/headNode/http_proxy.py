import sys
import os


import argparse
import asyncio
import uuid # For generating proxy_id
import httpx # For making HTTP requests to replicas
import grpc
from fastapi import FastAPI, Request, HTTPException # Added Request
from fastapi.responses import Response, PlainTextResponse
from starlette.responses import StreamingResponse # For streaming back the response
import uvicorn # For running FastAPI
from xml.dom.pulldom import parseString

from src.generated import headnode_service_pb2, headnode_service_pb2_grpc
from src.lib.proxy_manager import ProxyManager
from src.lib.deployment_manager import DeploymentManager
from src.lib.health_manager import HealthManager
from src.lib.deployment_handle import DeploymentHandle
from src.lib.configurations import proxy_ping_max_retries, proxy_ping_retry_delay
from src.generated import worker_service_pb2, worker_service_pb2_grpc, proxy_service_pb2, proxy_service_pb2_grpc
from src.generated import common_pb2 # Import common_pb2
from src.lib.model_config import model_config_manager

import json # Added back
import base64 # Added back

# --- FastAPI App Definition ---
app = FastAPI()

# --- Global HttpProxy instance ---
# This instance will be created in main() and used by FastAPI route handlers.
http_proxy_instance = None

# Global server reference for shutdown
grpc_server_instance = None

# --- HttpProxy Class ---
class HttpProxy():
    def __init__(self, parent_port, grpc_port):
        self.parent_port = parent_port
        self.grpc_port = grpc_port
        self.routing_lock = asyncio.Lock()
        self.routing_table: dict[str, DeploymentHandle] = {} 
        self.proxy_id = str(uuid.uuid4())
        self.http_client = httpx.AsyncClient() 
        # Start subscription to head node
        self.subscription_task = asyncio.create_task(self.subscribe_to_head_node())
        print(f"[HttpProxy:{self.proxy_id}] Initialized. Listening for HeadController on port {parent_port}.")
    
    
    async def close(self):
        """Gracefully close resources."""
        print(f"[HttpProxy:{self.proxy_id}] Closing resources...")
        if hasattr(self, 'subscription_task') and self.subscription_task:
            self.subscription_task.cancel()
            try:
                await self.subscription_task
            except asyncio.CancelledError:
                print(f"[HttpProxy:{self.proxy_id}] Subscription task cancelled.")
        await self.http_client.aclose()
        print(f"[HttpProxy:{self.proxy_id}] Resources closed.")
    
    async def apply_routing_update(self, update: headnode_service_pb2.RoutingUpdate):
        """Applies routing updates received from the HeadController."""
        print(f"[HttpProxy:{self.proxy_id}] Received routing update. Timestamp: {update.timestamp_ns}")
        async with self.routing_lock:
            self.routing_table = {}
        # Add new or update existing deployments
            for deployment_id, dep_info_proto in update.current_deployments.items():
                self.routing_table[dep_info_proto.deployment_name] = DeploymentHandle(deployment_id, dep_info_proto)
            print(f"[HttpProxy:{self.proxy_id}] Routing table updated. Current deployments: {list(self.routing_table.keys())}")
            
    
    async def subscribe_to_head_node(self):
        """Subscribes to routing updates from the HeadController."""
        while True:
            try:
                async with grpc.aio.insecure_channel(f"0.0.0.0:{self.parent_port}") as channel:
                    stub = headnode_service_pb2_grpc.ProxyManagementServiceStub(channel)
                    print(f"[HttpProxy] Subscribing to head node at {self.parent_port}")
                    request = headnode_service_pb2.SubscriptionRequest(proxy_id=self.proxy_id)
                    stream = stub.SubscribeToRoutingUpdates(request)
                    async for update in stream:
                        await self.apply_routing_update(update)
            except grpc.aio.AioRpcError as e:
                print(f"[HttpProxy:{self.proxy_id}] gRPC Error subscribing to HeadNode: {e.code()} - {e.details()}")
                retry_delay = 5
                if e.code() in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.CANCELLED):
                    print(f"[HttpProxy:{self.proxy_id}] Controller unavailable or stream cancelled. Retrying in {retry_delay}s...")
                else:
                    print(f"[HttpProxy:{self.proxy_id}] Unhandled gRPC error during subscription. Retrying in {retry_delay}s...")
            except Exception as e:
                print(f"[HttpProxy:{self.proxy_id}] An unexpected error occurred in subscription loop: {e}. Retrying in 5 seconds...")
        
            await asyncio.sleep(5)

    
    async def send_request_to_worker(self, deployment, message : str):
        return await deployment.send_request(message)
        
    # Method to handle HTTP request packaging and forwarding via gRPC
    def forward_request_to_replica(self, deployment_name: str, message: str):
        """
        Extracts the request body, sends it as a string to a replica via 
        DeploymentHandle.send_request (gRPC), and returns the replica's output
        as an HTTP StreamingResponse.
        """
        
        print(f"[HttpProxy] Forwarding streaming request to deployment '{deployment_name}'")
        
        async def stream_generator():
            """Generator that yields streaming tokens from the replica"""
            try:
                # Handle routing lock properly inside the async generator
                async with self.routing_lock:
                    deployment_handle = self.routing_table.get(deployment_name)
                    if not deployment_handle:
                        #print(f"[HttpProxy:{self.proxy_id}] Deployment '{deployment_name}' not found in routing table.")
                        yield f"data: {{'error': 'Deployment {deployment_name} not found', 'is_complete': true}}\n\n"
                        return
                
                
                async for token_data in deployment_handle.send_request(message):
                    #print(f"[HttpProxy:{self.proxy_id}] Yielding token data: {token_data[:100]}...")
                    yield token_data
            except Exception as e:
               yield "Error in streaming, retry"
        
        return StreamingResponse(
            stream_generator(), 
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  
            }
        )


  
@app.post("/{path:path}")
async def handle_process_string_request(request: Request):
    """
    Receives an HTTP POST request, treats its body as a string,
    sends it to the backend, and returns the response.
    """
    client_host = request.client.host if request.client else "unknown_client"
    request_id = str(uuid.uuid4()) # Unique ID for this request handling instance
    path = request.url.path
    #print(f"HTTP_HANDLER [{request_id}]: Received POST from {client_host} to {request.url.path}")

    http_body_bytes = await request.body()

    if not http_body_bytes:
        print(f"HTTP_HANDLER [{request_id}]: Request body is empty.")
        raise HTTPException(status_code=400, detail="Request body cannot be empty for processing.")
   
    try:
        input_string = http_body_bytes.decode('utf-8')
        print(f"HTTP_HANDLER [{request_id}]: Decoded body to string (len {len(input_string)}): '{input_string[:100]}...'")
    except UnicodeDecodeError:
        print(f"HTTP_HANDLER [{request_id}]: Failed to decode request body as UTF-8.")
        raise HTTPException(status_code=400, detail="Invalid UTF-8 sequence in request body.")

    
    try:
        # Use path directly since routing table is keyed by endpoint paths
        backend_response = http_proxy_instance.forward_request_to_replica(path, input_string)
        return backend_response  # Return immediately, let FastAPI handle the streaming
    except HTTPException: # Re-raise HTTPExceptions that might come from the forwarding logic
        return PlainTextResponse(content="\n Error in forwarding logic.Retry")
    except Exception as e: # Catch any other unexpected error from the forwarding logic
        print(f"HTTP_HANDLER [{request_id}]: Error in forwarding logic: {str(e)}")
        raise HTTPException(status_code=502, detail="Error communicating with backend service.")


class MinimalHealthServicer(proxy_service_pb2_grpc.HealthServiceServicer):
   

    async def Ping(self, request, context):
        print(f"[HttpProxy] Ping received")
        return common_pb2.Ack(acknowledged=True)



async def start_uvicorn(app, http_port):
    config = uvicorn.Config(app, host="0.0.0.0", port=http_port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def run_proxy_server(app, http_port, grpc_port, parent_port):
    global grpc_server_instance, http_proxy_instance
    
    # Create and assign the global HttpProxy instance here
    http_proxy_instance = HttpProxy(
        parent_port=parent_port,
        grpc_port=grpc_port
    )

    # Start gRPC server
    grpc_server_instance = grpc.aio.server()
    grpc_server_instance.add_insecure_port(f"[::]:{grpc_port}")
    proxy_service_pb2_grpc.add_HealthServiceServicer_to_server(MinimalHealthServicer(), grpc_server_instance)
    await grpc_server_instance.start()
    print(f"gRPC server running on port {grpc_port}")
   
    # Start both servers concurrently
    try:
        await asyncio.gather(
            start_uvicorn(app, http_port),
            grpc_server_instance.wait_for_termination()
        )
    except asyncio.CancelledError:
        print("[HttpProxy] Servers cancelled, shutting down...")
    finally:
        # Gracefully stop the gRPC server
        if grpc_server_instance:
            print("[HttpProxy] Stopping gRPC server...")
            await grpc_server_instance.stop(grace=5)

def main():
    global http_proxy_instance
    parser = argparse.ArgumentParser(description="HTTP Proxy for Model Serving System")
    parser.add_argument("--parent_port", type=int, required=True, help="Port of the HeadController gRPC server.")
    parser.add_argument("--http_port", type=int, default=8000, help="Port for this proxy's HTTP server.")
    parser.add_argument("--grpc_port", type=int, default=50052, help="Port for this proxy's gRPC server")
    args = parser.parse_args()

    # HttpProxy instance will be created in run_proxy_server
    
    try:
        asyncio.run(run_proxy_server(app, args.http_port, args.grpc_port, args.parent_port))
    except KeyboardInterrupt:
        print(f"\n[HttpProxy] Shutdown requested (KeyboardInterrupt)...")
    

if __name__ == "__main__":
    main()  

    

