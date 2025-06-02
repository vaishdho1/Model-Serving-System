import asyncio
import grpc
from typing import Dict, Any
from collections import deque
from grpc import StatusCode
from src.lib import FutureManager
from src.generated import headnode_service_pb2, worker_service_pb2, replica_service_pb2

class Replica:
    def __init__(self, pid, worker_id, stub, headnode_stub, deployment_id):
        self.pid = pid  # Using self.pid as the replica's identifier for logging
        self.worker_id = worker_id
        self.stub = stub # This is a synchronous stub
        self.headnode_stub = headnode_stub
        self.replica_queue = asyncio.Queue()
        self.status = "idle"  # "idle" or "processing"
        self._processing_task = None  # asyncio.Task for the _process_queue consumer
        self.deployment_id = deployment_id
    
    async def _try_send_with_retries(self, coroutine_function, request_message, max_attempts=3, delay_ms=100):
        """
        Tries to send a message with retries.
        """
        for attempt in range(max_attempts): 
            try:
                print(f"[Replica-{self.pid}] Attempt {attempt + 1} calling RPC. Request: {request_message}")
                return await coroutine_function (request_message)
            except grpc.aio.AioRpcError as e:
                if e.code() == grpc.StatusCode.UNAVAILABLE:
                    print(f"[Replica-{self.pid}] Attempt {attempt + 1} failed during send, retrying...")
                    await asyncio.sleep(delay_ms / 1000.0)
                else:
                    print(f"[Replica-{self.pid}] Unknown gRPC error during send: {e.code()} - {e.details()}")
                    raise  # Re-raise to be caught by the caller (_process_queue)
        print(f"[Replica-{self.pid}] Max send attempts reached for RPC.")
        raise Exception("Max send attempts reached")
   
   
    async def submit_task(self, input_data):
        """
        Submits a task to this replica's queue.
        Returns a future that will be resolved with the task's output string or an exception.
        """
        stream_queue = asyncio.Queue()
        print(f"[Replica-{self.pid}] Waiting to submit task to queue. Queue size: {self.replica_queue.qsize()}")
        await self.replica_queue.put((input_data, stream_queue))
        print(f"[Replica-{self.pid}] Submitted task to queue. Queue size: {self.replica_queue.qsize()}")

        if self.status == "idle" or self._processing_task is None:
            print(f"[Replica-{self.pid}] Starting/restarting task processing loop.")
            self.status = "processing"
            self._processing_task = asyncio.create_task(self._process_queue())
       
        return stream_queue

    async def _process_queue(self):
        """
        A long-running task that consumes from self.replica_queue and processes tasks.
        """
        print(f"[Replica-{self.pid}] Task processing consumer started.")
        
        while True:
            input_data, stream_queue = None, None
            try:
                print(f"[Replica-{self.pid}] Waiting for task from queue (size: {self.replica_queue.qsize()}). Status: {self.status}")
                input_data, stream_queue = await self.replica_queue.get()
                
                self.status = "processing"

                print(f"[Replica-{self.pid}] Got task from queue. Processing...")

                task_request = replica_service_pb2.PromptRequest(prompt=input_data)

               
                async for chunk in self.stub.StreamGenerate(task_request):
                    await stream_queue.put(replica_service_pb2.TokenChunk(text=chunk.text, is_error=False))
                    print(f"[Replica-{self.pid}] Sent chunk to stream_queue: {chunk.text}")
                await stream_queue.put(None)

            except asyncio.CancelledError:
                print(f"[Replica-{self.pid}] Task processing consumer loop was cancelled.")
                await stream_queue.put(replica_service_pb2.TokenChunk(text="gRPC stream failed", is_error=True))
                self.status = "idle"
                self._processing_task = None
                raise

            except Exception as e:
                print(f"[Replica-{self.pid}] Exception: {e}")
                await stream_queue.put(replica_service_pb2.TokenChunk(text=f"gRPC stream failed: {e}", is_error=True))

            finally:
                if self.replica_queue.qsize() == 0 and self.status == "processing":
                    print(f"[Replica-{self.pid}] Queue is empty after processing. Setting status to idle.")
                    self.status = "idle"

                    
        
        

    