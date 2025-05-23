import asyncio
import grpc
from typing import Dict, Any
from src.generated import headnode_service_pb2, headnode_service_pb2_grpc
import configurations
import time
import os
import signal
class HeadStoreClient:
    def __init__(self, head_address, port):
        self.head_address = head_address
        self.port = port
        # Currently connects to the headnode
        self.channel = grpc.aio.insecure_channel(f"{head_address}:{port}")
        self._stub = headnode_service_pb2_grpc.HeadNodeServiceStub(self.channel)

    def register_node(self, node_info):
        '''
        Todo:Need to be more explicit about node_id
        Check different error types
        See how to get configurations from the environment file

        '''
        # Register the node with the head node
        request = headnode_service_pb2.RegisterRequest(
            node_id = int(node_info["node_id"]),
            node_address = str(node_info["node_address"]),
            port = str(node_info["port"]),
            state = str(node_info["resources"])
        )
        cur_retries = 0
        while cur_retries < configurations.head_store_max_retries:
            try:
                response = self._stub.RegisterNode(request, timeout = configurations.head_store_timeout)
                print(f"Node registered with head node: {response}")
                return response
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.UNAVAILABLE:
                    print(f"Head node unavailable, retrying in {configurations.head_store_retry_delay} seconds...")
            time.sleep(configurations.head_store_retry_delay)
            cur_retries += 1
        
        #Kill the process if we cannot connect to the head node
        print("Failed to register node with head node after multiple attempts.")
        os.kill(os.getpid(), signal.SIGTERM)

    async def ReportNodeHealth(self, node_id, status, replica_state):
        print(f"[HeadStoreClient-ASYNC] Preparing to send health report for node {node_id}...")
        request = headnode_service_pb2.HealthStatusUpdate(
            worker_id=node_id, 
            state=status, 
            replica_states=replica_state
        )
        try:
            # Using the async_stub (self._stub) initialized in __init__
            response = await self._stub.SendHealthStatus(request, timeout=configurations.head_store_timeout if hasattr(configurations, 'head_store_timeout') else 5) # Added timeout
            print(f"[HeadStoreClient-ASYNC] Health report sent. Response: {response}")
            return response
        except grpc.aio.AioRpcError as e: # Catch specific async gRPC errors
            print(f"[HeadStoreClient-ASYNC] Async GRPC error during ReportNodeHealth: Code: {e.code()}, Details: {e.details()}")
            return None 
        except Exception as e:
            print(f"[HeadStoreClient-ASYNC] Non-GRPC error during ReportNodeHealth: {e}")
            return None
    

        await self._stub.SendHealthStatus(headnode_service_pb2.HealthStatusUpdate(worker_id = node_id, state = status, replica_states = replica_state))
    