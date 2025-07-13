from typing import List, Optional
import random
import asyncio
import grpc
from dataclasses import dataclass
from src.generated import worker_service_pb2, worker_service_pb2_grpc, replica_service_pb2, replica_service_pb2_grpc
from src.lib.helpers import try_send_with_retries, send_with_delay


import time
#This takes an input from the proxy and stores it

@dataclass
class ReplicaInfo:
    replica_id : str  # Format: worker_id#actual_replica_id
    replica_address : str  # Replica address
    state : str


class DeploymentHandle:
    def __init__(self, deployment_id: str, DeploymentObj):
        self.deployment_id = deployment_id
        self.deployment_name = getattr(DeploymentObj, 'deployment_name', 'UnknownDeployment')
        self.version = getattr(DeploymentObj, 'version', 'UnknownVersion')

        self.replica_cache = {}  # Stores replica_id -> outstanding_request_count
        self.replicas: List[ReplicaInfo] = self._initialize_replicas_and_cache(
            getattr(DeploymentObj, 'replicas', []) 
        )
        self.replica_lock = asyncio.Lock()
        
   

    #Made this blocking for now
    def _initialize_replicas_and_cache(self, replicas:List):
        replica_list = []
        for replica in replicas:
            replica_list.append(ReplicaInfo(replica.replica_id, replica.address, replica.state))
            if replica.state == "RUNNING" and replica.replica_id not in self.replica_cache:
                self.replica_cache[replica.replica_id] = 0
            if replica.state == "SHUTDOWN" and replica.replica_id in self.replica_cache:
                del self.replica_cache[replica.replica_id]

        #Remove any replicas that are not in the new deployment info
        #current_ids = [replica.replica_id for replica in replicas]
        #for replica_id in self.replica_cache:
        #    if replica_id not in current_ids:
        #        del self.replica_cache[replica_id]
        return replica_list
   
    def _parse_replica_id(self, full_replica_id: str):
        """
        Parse replica_id in format 'worker_id#actual_replica_id'
        Returns: (worker_id, actual_replica_id)
        """
       
        parts = full_replica_id.split('#', 1)
        return parts[0], parts[1]
       
    
    async def pick_next_replica(self):
        #Picks the least loaded replica and the second least loaded replica for routing
        async with self.replica_lock:
            running_replicas = [r for r in self.replicas if r.state == "RUNNING"]
            selected_replica = min(running_replicas, key=lambda r: self.replica_cache.get(r.replica_id, 0))
            current_count = self.replica_cache.get(selected_replica.replica_id, 0)
            self.replica_cache[selected_replica.replica_id] = current_count + 1
            print(f"[DeploymentHandle] Picked {selected_replica.replica_id}, new count: {self.replica_cache[selected_replica.replica_id]}")
            return selected_replica.replica_address, selected_replica.replica_id

        
            
    async def _attempt_streaming_request_to_worker_node(self, 
                                                        full_replica_id: str,
                                                        replica_address: str,
                                                        message: str):
        """
        Send a streaming request to the WorkerNode which will forward it to the specified replica.
        """
       
        if not full_replica_id or not replica_address:
            print(f"[DeploymentHandle:{self.deployment_id}] Invalid replica_id or replica_address provided for streaming attempt.")
            return

        # Parse the replica ID to get the actual replica ID
        worker_id, actual_replica_id = self._parse_replica_id(full_replica_id)
        #print(f"[DeploymentHandle:{self.deployment_id}] Parsed replica_id '{full_replica_id}' -> worker_id='{worker_id}', actual_replica_id='{actual_replica_id}'")

        try:
            # Increment request count
            async with self.replica_lock:
                if full_replica_id not in self.replica_cache:
                    print(f"[DeploymentHandle:{self.deployment_id}] Warning: Replica {full_replica_id} not in cache for count increment. Aborting attempt.")
                    return 
                
            # Connect to WorkerNode and submit streaming task
            async with grpc.aio.insecure_channel(replica_address) as channel:
                # New Design:Use directly the replica service stub 
                stub = replica_service_pb2_grpc.WorkerServiceStub(channel)
                
                print(f"[DeploymentHandle:{self.deployment_id}] Sending streaming request to Replica at {replica_address} for replica {actual_replica_id}...")
                
                # Create ReplicaRequest for the Replica
                request = replica_service_pb2.ReplicaRequest(
                    prompt=message
                )
                
                # Call SendRequest method on WorkerNode (returns a stream)
                stream_response = stub.SendRequest(request)
                
                # Stream tokens back as they arrive from the WorkerNode
                async for replica_reply in stream_response:
                    if replica_reply.is_error:
                        #print(f"[DeploymentHandle:{self.deployment_id}] Error from WorkerNode for replica {actual_replica_id}: {replica_reply.output}")
                        raise Exception(f"Error Replica {actual_replica_id}: from worker {worker_id}: {replica_reply.text}")
                        
                    else:
                        # Stream the token back to HTTP proxy
                        token_text = replica_reply.text
                    
                       
                        yield token_text
                
                # Signal completion
                
                print(f"[DeploymentHandle:{self.deployment_id}] Streaming completed for replica {actual_replica_id}")

        except grpc.aio.AioRpcError as e:
            raise Exception(f"gRPC error with Replica at {replica_address} for replica {actual_replica_id}: {e.code()} - {e.details()}")
        except Exception as e:
            raise Exception(f"Error in streaming request to Replica for replica {actual_replica_id}: {e}")
        finally:
            # Decrement request count
            async with self.replica_lock:
                if full_replica_id in self.replica_cache:
                    self.replica_cache[full_replica_id] -= 1
                    if self.replica_cache[full_replica_id] < 0:
                        self.replica_cache[full_replica_id] = 0 
                    print(f"[DeploymentHandle:{self.deployment_id}] Decremented count for {full_replica_id} to {self.replica_cache[full_replica_id]}.")

    
    async def send_request(self, message: str):
        """
        Send a streaming request to the best available replica via the WorkerNode.
        This method returns an async generator that yields Server Sent Events.
        """
        
        replica_address, replica_id = await self.pick_next_replica()
        
       
        
        print(f"[DeploymentHandle:{self.deployment_id}] Starting streaming request via WorkerNode.")

        # Try the replica
        if replica_id and replica_address:
            print(f"[DeploymentHandle:{self.deployment_id}]  Targeting replica {replica_id} via WorkerNode at {replica_address}.")
            try:
                async for token_data in self._attempt_streaming_request_to_worker_node(replica_id, replica_address, message):
                    #print(f"[DeploymentHandle:{self.deployment_id}] Sending token: '{token_data}'")
                    yield token_data
                return  # Successfully streamed, return
            except Exception as e:
                print(f"Error in streaming request to WorkerNode for replica {replica_id}: {e}")
        else:
           raise Exception(f"No valid replicas found")

        
       
       
