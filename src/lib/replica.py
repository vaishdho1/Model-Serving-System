import asyncio
import grpc
from typing import Dict, Any
from collections import deque
from grpc import StatusCode
from src.lib import FutureManager
from src.generated import headnode_service_pb2, worker_service_pb2, replica_service_pb2

class Replica:
    def __init__(self, pid, replica_id, worker_id, stub, headnode_stub, deployment_id, port):
        self.pid = pid  # Using self.pid as the replica's identifier for logging
        self.replica_id = replica_id
        self.worker_id = worker_id
        self.stub = stub # This is a synchronous stub
        self.headnode_stub = headnode_stub
        self.status = "idle"  # "idle" or "processing"
        self.deployment_id = deployment_id
        self.active_requests = 0
        self.port = port
        #self.max_concurrent_requests = 128  # Limit concurrent requests per replica
       

    async def submit_task(self, input_data):
        """
        Submits a task by immediately creating a concurrent worker for it.
        Returns the queue that the worker will use to stream results.
        """
        stream_queue = asyncio.Queue()
        print(f"[Replica-{self.pid}] Immediately creating a processing task for new request.")
        
        # For every new task, create a new, independent processing coroutine.
        asyncio.create_task(self._process_individual_task(input_data, stream_queue))
       
        return stream_queue

    # REMOVED: _send_batched_requests method - no longer needed

    async def _process_individual_task(self, input_data, stream_queue):
        """
        This coroutine handles exactly one request and then exits.
        Multiple instances of this will run concurrently.
        """
        print(f"[Replica-{self.pid}] Starting gRPC stream for a single task.")
        try:
            self.status = "processing"
            task_request = replica_service_pb2.PromptRequest(prompt=input_data)

            # Make the gRPC call. This will run concurrently with other calls.
            async for chunk in self.stub.StreamGenerate(task_request):
                
                await stream_queue.put(replica_service_pb2.TokenChunk(text=chunk.text, is_error=False)) # Forward the chunk directly

            # Signal the end of the stream to the consumer.
            await stream_queue.put(None)

        except grpc.aio.AioRpcError as e:
            print(f"[Replica-{self.pid}] gRPC Error during stream: {e.code()} - {e.details()}")
            await stream_queue.put(replica_service_pb2.TokenChunk(text=f"gRPC stream failed: {e.details()}", is_error=True))
        except Exception as e:
            print(f"[Replica-{self.pid}] Exception in task processing: {e}")
            await stream_queue.put(replica_service_pb2.TokenChunk(text=f"Generic error in stream: {e}", is_error=True))

    
   
                    
        
        

    