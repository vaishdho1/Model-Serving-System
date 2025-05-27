import argparse
import asyncio
from xml.dom.pulldom import parseString
import grpc
from fastapi import FastAPI, HTTPException
from src.generated import headnode_service_pb2, headnode_service_pb2_grpc
from src.lib import ProxyManager, DeploymentManager, AutoScaleManager, HealthManager, DeploymentHandle
from src.lib.configurations import proxy_ping_max_retries, proxy_ping_retry_delay
from src.lib.deployment_manager import DeploymentManager
from src.lib.proxy_manager import ProxyManager
from src.lib.health_manager import HealthManager
from src.generated import worker_service_pb2, worker_service_pb2_grpc
app = FastAPI()
# This needs to run a  grpc server and a http server
class HttpProxy():
    def __init__(self, parent_port, http_port, grpc_port):
        #Currently assumes that the parent and the proxy are running on the same machine
        self.parent_port = parent_port
        self.http_port = http_port
        self.routing_table = {}
        self.replica_cache = {} # This is a dictionary of replica_id -> Queue of requests dispatched
        # Create a subscription to the head node as a separate task
        asyncio.create_task(self.subscribe_to_head_node())

   
  
      
    # This completely replaces the routing table on update
    def apply_routing_update(self, update: headnode_service_pb2.RoutingUpdate):
        # This updates the local routing table
        for deployment_id in update.current_deployments:
            dep_object = DeploymentHandle(deployment_id, update.current_deployments[deployment_id])
            self.routing_table[deployment_id] = dep_object
        
        print(f"[HttpProxy] Routing table updated: {self.routing_table}")


    # Creates a subscription channel to the head node
    async def subscribe_to_head_node(self):
        while True:
            try:
                async with grpc.aio.insecure_channel(f"localhost:{self.parent_port}") as channel:
                    stub = headnode_service_pb2_grpc.HeadNodeServiceStub(channel)
                    print(f"[HttpProxy] Subscribing to head node at {self.parent_port}")
                    request = headnode_service_pb2.SubscriptionRequest(proxy_id=self.proxy_id)
                    stream = stub.SubscribeToRoutingUpdates(request)
                    async for update in stream:
                        # This updates the local routing table
                        self.apply_routing_update(update)
            except grpc.aio.AioRpcError as e:
                print(f"[httpProxy] gRPC Error: {e.code()} - {e.details()}")
                if e.code() == grpc.StatusCode.UNAVAILABLE:
                    print(f"[httpProxy] Controller unavailable. Retrying in 5 seconds...")
                elif e.code() == grpc.StatusCode.CANCELLED:
                    print(f"[httpProxy] Stream cancelled by server. Retrying in 5 seconds...")
                else:
                    print(f"[httpProxy] Unhandled gRPC error. Retrying in 5 seconds...")
            except Exception as e:
                print(f"[HttpProxy:{self.proxy_id}] An unexpected error occurred in subscription loop: {e}. Retrying in 5 seconds...")
        
            await asyncio.sleep(5)

    # FastAPI route handlers need to be at the top level or registered with an APIRouter
    # They cannot be methods of HttpProxy class directly if using @app.route decorator
    # unless app is passed into HttpProxy or routes are added dynamically.
    # For simplicity, making handle_request a top-level async function that uses the global http_proxy_instance.
    async def send_request_to_worker(self, deployment:DeploymentHandle, message : str):
        return await deployment.send_request(message)
        


def main():
    global http_proxy_instance # Allow main to set the global instance

    parser = argparse.ArgumentParser(description="HTTP Proxy for Model Serving")
    parser.add_argument("--parent_port", type=int, required=True, help="Port of the HeadController gRPC server.")
    parser.add_argument("--http_port", type=int, default=8000, help="Port for this proxy's HTTP server.")
    parser.add_argument("--grpc_port", type=int, default=50052, help="Port for this proxy's gRPC server (if any).")
    # Add proxy_id as an optional argument if needed, otherwise it's auto-generated
    # parser.add_argument("--proxy_id", type=str, help="Unique ID for this proxy instance.")
    args = parser.parse_args()

    
if __name__ == "__main__":
    main()

    
