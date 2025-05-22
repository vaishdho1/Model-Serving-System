import asyncio
import grpc
from typing import Dict, Any
from collections import deque
from grpc import StatusCode
from future_manager import FutureManager
import headnode_service_pb2
import worker_service_pb2

class Replica:
    def __init__(self, pid, worker_id, stub, headnode_stub):
        self.pid = pid  # Using self.pid as the replica's identifier for logging
        self.worker_id = worker_id
        self.stub = stub
        self.headnode_stub = headnode_stub
        self.replica_queue = asyncio.Queue()
        self.status = "idle"  # "idle" or "processing"
        self._processing_task = None  # asyncio.Task for the _process_queue consumer
    
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
    
    async def submit_task(self, input_data: headnode_service_pb2.Message):
        """
        Submits a task to this replica's queue.
        Returns a future that will be resolved with the task's output string or an exception.
        """
        task_future = asyncio.Future()
        await self.replica_queue.put((input_data, task_future))
        print(f"[Replica-{self.pid}] Submitted task to queue. Queue size: {self.replica_queue.qsize()}")

        if self.status == "idle" or self._processing_task is None:
            print(f"[Replica-{self.pid}] Starting/restarting task processing loop.")
            self.status = "processing"
            self._processing_task = asyncio.create_task(self._process_queue())
       
        
        return task_future

    async def _process_queue(self):
        """
        A long-running task that consumes from self.replica_queue and processes tasks.
        """
        print(f"[Replica-{self.pid}] Task processing consumer started.")
        
        while True:
            input_data, current_task_future = None, None
            try:
                print(f"[Replica-{self.pid}] Waiting for task from queue (size: {self.replica_queue.qsize()}). Status: {self.status}")
                input_data, current_task_future = await self.replica_queue.get()
                
                self.status = "processing"

                print(f"[Replica-{self.pid}] Got task from queue. Processing...")
                
                task_request = worker_service_pb2.TaskRequest(
                    model=input_data.model,
                    input=input_data.input
                )
                print(f"[Replica-{self.pid}] Sending task to actual worker replica. Request object: {task_request}")
                
                worker_output = await self._try_send_with_retries(
                    coroutine_function=self.stub.PushTask,
                    request_message=task_request
                )
                
                
                print(f"[Replica-{self.pid}] Received output from worker: {worker_output.result}")
                current_task_future.set_result(worker_output.result)
                

            except asyncio.CancelledError:
                print(f"[Replica-{self.pid}] Task processing consumer loop was cancelled.")
                if current_task_future and not current_task_future.done():
                    current_task_future.set_exception(asyncio.CancelledError())
                self.status = "idle" # Reset status
                self._processing_task = None # Clear own task reference
                raise # Propagate cancellation to stop this consumer task
            except Exception as e:
                print(f"[Replica-{self.pid}] Exception in task processing consumer loop: {e}")
                if current_task_future and not current_task_future.done():
                    current_task_future.set_exception(e)
                # Continue to the next item in the queue
            finally:
                if self.replica_queue.qsize() == 0:
                     if self.status == "processing": # If we were processing and queue is now empty
                        print(f"[Replica-{self.pid}] Queue is empty after processing. Setting status to idle.")
                        self.status = "idle"

                
        
        # print(f"[Replica-{self.pid}] Task processing consumer loop ended (should not happen if while True).")
        # self.status = "idle"
        # self._processing_task = None

    