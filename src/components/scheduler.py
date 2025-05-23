from concurrent import futures
import grpc
from src.generated import headnode_service_pb2, worker_service_pb2, worker_service_pb2_grpc, headnode_service_pb2_grpc

import multiprocessing
import grpc
from dataclasses import dataclass
from concurrent import futures
import subprocess
import time
import os

import argparse
from src.lib import configurations, FutureManager, HeadStoreClient, Replica
import signal
import asyncio
from google.protobuf import empty_pb2
replica_lock = asyncio.Lock()
'''
This is the code of a general worker node scheduler.
When a worker node is started it registers with the head node and then starts a health monitor thread.
'''
node_id = 1

replica_num = 0
replica_registry = {}
# Create a replica futures to return requests to the head node
replica_futures = FutureManager()


async def try_send_with_retries(coro_func, *args, num_attempts=3, delay_seconds=2, **kwargs):
    """Helper function to retry an async operation that might raise grpc.RpcError."""
    last_exception = None
    for attempt in range(1, num_attempts + 1):
        try:
            #print(f"[RetryHelper] Attempt {attempt}/{num_attempts} calling {coro_func.__name__}") # Optional: for more verbose logging
            return await coro_func(*args, **kwargs)
        except grpc.RpcError as e:
            print(f"[RetryHelper] Attempt {attempt}/{num_attempts} failed for {getattr(coro_func, '__name__', 'rpc_call')}: {e.code()} - {e.details()}")
            last_exception = e
            if attempt < num_attempts:
                print(f"[RetryHelper] Retrying in {delay_seconds} seconds...")
                await asyncio.sleep(delay_seconds)
        # Consider if other exceptions should be caught and retried, or allowed to propagate immediately.
    
    return None
def send_with_delay(coro_func, *args, num_attempts=3, delay_seconds=2, **kwargs):
    """Helper function to retry an async operation that might raise grpc.RpcError."""
    last_exception = None
    for attempt in range(1, num_attempts + 1):
        try:
            #print(f"[RetryHelper] Attempt {attempt}/{num_attempts} calling {coro_func.__name__}") # Optional: for more verbose logging
            return coro_func(*args, **kwargs)
        except grpc.RpcError as e:
            print(f"[RetryHelper] Attempt {attempt}/{num_attempts} failed for {getattr(coro_func, '__name__', 'rpc_call')}: {e.code()} - {e.details()}")
            last_exception = e
            if attempt < num_attempts:
                print(f"[RetryHelper] Retrying in {delay_seconds} seconds...")
                time.sleep(delay_seconds)
        # Consider if other exceptions should be caught and retried, or allowed to propagate immediately.
    
    return None

def _register_node(worker_id, node_address, node_port, head_address, head_port):
        # Register the node with the head node
        print(f"[Scheduler-{worker_id}] Registering node...")
        request_msg = headnode_service_pb2.RegisterRequest(
            node_id = int(worker_id),
            node_address = str(node_address),
            port = str(node_port),
            state = "alive"
        )

        max_retries = getattr(configurations, 'head_store_max_retries', 3)
        retry_delay = getattr(configurations, 'head_store_retry_delay', 2)
        timeout_duration = getattr(configurations, 'head_store_timeout', 5) # Timeout for the RPC call itself
        registration_successful = False

        for attempt in range(max_retries):
            print(f"[Scheduler-{worker_id}] Registration attempt {attempt + 1}/{max_retries} to {head_address}:{head_port}")
            try:
                # Create channel and stub for each attempt to ensure freshness if previous attempt failed connection
                with grpc.insecure_channel(f"{head_address}:{head_port}") as channel:
                    # Optionally, wait for channel to be ready (for synchronous channel)
                    # grpc.channel_ready_future(channel).result(timeout=timeout_duration) # Can add a connection timeout here
                    stub = headnode_service_pb2_grpc.HeadNodeServiceStub(channel)
                    response = stub.RegisterNode(request_msg, timeout=timeout_duration)
                    if response and response.ack:
                        print(f"[Scheduler-{worker_id}] Node successfully registered. Ack: {response.ack}")
                        registration_successful = True
                        # self.hsclient could be marked as ready/initialized here if it were fully async
                        # For now, we rely on this method's success for the scheduler to proceed.
                        break # Exit retry loop on success
                    else:
                        print(f"[Scheduler-{worker_id}] Registration acknowledged but ack was not True. Response: {response}")
                        # Treat as failure, will retry if attempts left

            except grpc.RpcError as e:
                print(f"[Scheduler-{worker_id}] GRPC error during registration attempt {attempt + 1}: {e.code()} - {e.details()}")
                if e.code() == grpc.StatusCode.UNAVAILABLE or e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                    if attempt < max_retries - 1:
                        print(f"[Scheduler-{worker_id}] Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                    else:
                        print(f"[Scheduler-{worker_id}] Max retries reached for gRPC error.")
                else:
                    print(f"[Scheduler-{worker_id}] Non-retryable gRPC error during registration. Aborting.")
                    break # Abort for non-UNAVAILABLE errors
            except Exception as e_gen:
                print(f"[Scheduler-{worker_id}] Generic error during registration attempt {attempt + 1}: {e_gen}")
                if attempt < max_retries - 1:
                    print(f"[Scheduler-{worker_id}] Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"[Scheduler-{worker_id}] Max retries reached for generic error.")
        
        if not registration_successful:
            print(f"[Scheduler-{worker_id}] CRITICAL: Failed to register node with head node after {max_retries} attempts. This scheduler might not function correctly or be recognized.")
            # In a robust system, you might want to os.kill(os.getpid(), signal.SIGTERM) or raise an exception here
            # to prevent the scheduler from running in an unregistrable state.
            # For now, it will proceed, but ReportNodeHealth will likely fail if hsclient is not properly working.
        else:
            print(f"[Scheduler-{worker_id}] Node registration process complete.")
        
        # The original print('output', output.ack) and print Node registered are now within the loop success case.
        # The self.hsclient.register_node(node_info) line was correctly commented out by you.


class HeadNodeManager(headnode_service_pb2_grpc.HeadNodeServiceServicer):
    def __init__(self, node_id, node_address, node_port, head_address, head_port, hs_client_instance):
        self.worker_id = node_id
        self.hsclient = hs_client_instance # Store the passed hsclient
        self.node_address = node_address
        self.node_port = node_port 
        self.head_address = head_address
        self.head_port = head_port
        # register the node with the head node
        #self._register_node()
        # Send regular health updates as a separate thread
    
        
    
    async def health_monitor(self):
        while True:
            for actor_id in self.actors:
                status = self.actors[actor_id]["health"]
                await self.headnode.receive_health_status(actor_id, status)
            await asyncio.sleep(5)  # simulate periodic check

    async def cleanup_replicas(self):
        global replica_registry
        print(f"[Scheduler-{self.worker_id}] Starting replica cleanup...")
        async with replica_lock:
            initial_count = len(replica_registry)
            replica_registry = { 
                replica_id: rinfo for replica_id, rinfo in replica_registry.items() 
                if rinfo.status != "dead" 
            }
            final_count = len(replica_registry)
        print(f"[Scheduler-{self.worker_id}] Replica cleanup complete. Removed {initial_count - final_count} dead replicas.")

    async def send_kill_signal(self):
        async with replica_lock:
            replica_snapshot = list(replica_registry.items())
        for replica_id, values in replica_snapshot:
            try:
                os.kill(values.pid, signal.SIGTERM)
            except Exception as e:
                print(f"[Scheduler-{self.worker_id}] Error sending SIGTERM to replica_id: {replica_id} (PID: {values.pid}): {e}")
        print(f"[Scheduler-{self.worker_id}] Finished sending kill signals to replicas.")
        os.kill(os.getpid(), signal.SIGTERM)
        
    async def _send_health_updates(self):
        '''
        Todo: Check frequency
        '''
        #count = 0
        while True:
            print("Sending health updates")
            current_replica_states = []
            # Cleanup any dead replicas
            
            await self.cleanup_replicas()
            #count += 1
            async with replica_lock:
                current_replica_state = list(replica_registry.items())
            
            replica_state_pbs_list = []
            try:
                replica_state_pbs_list = [ # Renamed to avoid conflict if 'replica_state' is used later
                    headnode_service_pb2.ReplicaState(
                        replica_id=replica_id, 
                        queue_size=values.replica_queue.qsize() if hasattr(values, 'replica_queue') else 0, # Defensive access
                        status=values.status if hasattr(values, 'status') else "unknown" # Defensive access
                    ) for replica_id, values in current_replica_state
                ]
            except Exception as e_comp:
                print(f"[Scheduler-{self.worker_id}] CRITICAL ERROR: Exception during replica_state list comprehension: {e_comp}")
                # Decide how to handle: continue with empty list, re-raise, etc.
                # For now, it will continue with an empty or partially filled list if error is mid-list (though list comp won't partially fill like this)
            
            print(f"[Scheduler-{self.worker_id}] Attempting to send health report for node {self.worker_id} with {len(replica_state_pbs_list)} replica states...")
            output = await try_send_with_retries(
                    self.hsclient._stub.SendHealthStatus, 
                    request = headnode_service_pb2.HealthStatusUpdate(
                        worker_id=self.worker_id, 
                        state="running", 
                        replica_states=replica_state_pbs_list # Use the new list name
                    ),
                    num_attempts= 3, # Example: 3 attempts
                    delay_seconds= 2 # Example: 2 seconds delay
            )
            
            if output is None or output.ack == 0:
                    print(f"[Scheduler-{self.worker_id}] Head node reported scheduler (node_id: {self.worker_id}) as unhealthy (ack=0). Initiating shutdown...")
                    await self.send_kill_signal()
                    return # Exit thread
                 
            print(f"[Scheduler-{self.worker_id}] Health update cycle complete. Output: {output}. Sleeping for {configurations.scheduler_health_update_interval}s.")
            await asyncio.sleep(configurations.scheduler_health_update_interval) 

    async def CreateReplica(self, request, context):
        global replica_num
        replica_id = -1 # To store the ID generated under lock

        async with replica_lock: 
            replica_num += 1
            replica_id = replica_num
        
        num_resources = request.num_resources
        resource_name = request.resource_name

        print(f"[Scheduler-{self.worker_id}] Preparing to create Replica with auto-generated ID: {replica_id}")
        
        # Define a unique port for the replica itself
        # Example: 50100 is a base, add replica_id modulo some number to vary it
        # Ensure this range doesn't conflict with other services.
        replica_port = 50100 + (replica_id % 1000) 

        cmd = [
            "python3", "add_replica.py", 
            "--replica_id", str(replica_id), 
            "--num_resources", str(num_resources), 
            "--resource_type", resource_name, 
            "--parent_port", str(self.node_port), # Port of this scheduler node
            "--port", str(replica_port)      # Port for the new replica's server
        ]
        print(f"[Scheduler-{self.worker_id}] Starting replica process for ID {replica_id} with command: {' '.join(cmd)}")
        
        try:
            # Open a log file for the replica
            log_file_name = f"replica_{replica_id}.log"
            print(f"[Scheduler-{self.worker_id}] Redirecting output of replica {replica_id} to {log_file_name}")
            with open(log_file_name, "w") as log_file:
                subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        except Exception as e:
            print(f"[Scheduler-{self.worker_id}] Failed to start replica process for ID {replica_id}: {e}")
            
            error_reply = headnode_service_pb2.ReplicaCreationReply(
                worker_id=self.worker_id, 
                replica_id=replica_id, 
                created=False 
                
            )
            replica_futures.set_result(replica_id, error_reply)
            return error_reply # Return the error reply directly to the gRPC client

        print(f"[Scheduler-{self.worker_id}] Replica process for ID {replica_id} initiated. Waiting for its registration...")
        fut = replica_futures.create_future(replica_id)
        return await fut # This will wait for WorkerManager.RegisterReplica to call replica_futures.set_result
    
    
    async def SendRequest(self, request, context):
        worker_id = request.worker_id
        replica_id = request.replica_id
        message = request.message  
        print(f"[Scheduler-{self.worker_id}] Received request from worker_id: {worker_id} to replica_id: {replica_id} with message: {message}")
        async with replica_lock:
            target_replica = replica_registry.get(replica_id)
        try:
            # submit_task now returns a future
            task_future = await target_replica.submit_task(message)
            print(f"[Scheduler-{self.worker_id}] Task submitted to replica {replica_id}. Waiting for result...")
            
            # Wait for the future to be resolved
            # You might want to add a timeout here in a production system
            task_output_str = await task_future 
            
            print(f"[Scheduler-{self.worker_id}] Result received from replica {replica_id}: {task_output_str}")
            return headnode_service_pb2.ReplicaReply(
                worker_id=worker_id,
                replica_id=replica_id,
                output=task_output_str
            )
        except Exception as e:
            print(f"[Scheduler-{self.worker_id}] Error during task processing for replica {replica_id}: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error processing task: {e}")
            return headnode_service_pb2.ReplicaReply() # Return empty or error-indicating reply
    
    
   
   
class WorkerManager(worker_service_pb2_grpc.WorkerServiceServicer):
    def __init__(self, node_id, hs_client_instance): # Allow optional node_id for logging/identification
        self.worker_id = node_id
        self.hsclient = hs_client_instance # Store the passed hsclient

    async def RegisterReplica(self, request, context):

        '''
        Once a replica registers, a stub is created to it and stored along with other information
        '''
        replica_id = request.replica_id
        pid = request.pid
        worker_stub = worker_service_pb2_grpc.WorkerServiceStub(grpc.aio.insecure_channel(f"localhost:{request.port}"))
        print(f"[WorkerManager-{self.worker_id}] Registering replica_id: {replica_id} (PID: {pid}) with port: {request.port} and state: {request.state}")
        replica_handle  = Replica(pid = pid, worker_id = self.worker_id, stub =  worker_stub, headnode_stub = self.hsclient._stub)
        async with replica_lock:
            replica_registry[replica_id] = replica_handle
        # Returns to the create replica call which is eaitinf on thie replca ID
        replica_futures.set_result(replica_id, headnode_service_pb2.ReplicaCreationReply(worker_id = self.worker_id, replica_id = replica_id, created = 1))
        # Acknowledgement to the replica
        return worker_service_pb2.Reply(ack=1)
    
    
    #From worker node
    async def sendHealthupdate(self, request, context):
        # Randomly decide to Ack or Nack
        # For example, 30% chance of sending a Nack (ack=0)
        #should_nack = random.random() < 0.3 # 30% chance to be True
        
        #print(f"[WorkerManager-{self.worker_id}] Received health update for replica_id: {request.replica_id} with status: {request.status}: {time.time()}")
        #if should_nack:
        #        print(f"[WorkerManager-{self.worker_id}] Intentionally NACKing health update for replica_id: {request.replica_id}.")
        #        return worker_service_pb2.HealthReply(ack=False)
        
        async with replica_lock:
            replica_info = replica_registry.get(request.replica_id)
      
        if replica_info is None or replica_info.status == "dead": 
            print(f"[WorkerManager-{self.worker_id}] Replica {request.replica_id} not found or dead. Sending NACK.")
            return worker_service_pb2.HealthReply(ack=False)
        else:
                print(f"[WorkerManager-{self.worker_id}] Replica {request.replica_id} is healthy. Sending ACK.")
                return worker_service_pb2.HealthReply(ack=True)
    

    async def start_heartbeat_loop(self):
        while True:
            snapshot_for_ping = []
            async with replica_lock:
                snapshot_for_ping = list(replica_registry.items())

            dead_replica_ids = []
            for replica_id, replica_info in snapshot_for_ping:
                
                print(f"[WorkerManager-{self.worker_id}] Pinging replica_id: {replica_id} (PID: {replica_info.pid})...")
                # Wrap the Ping call with the retry helper
                output = await try_send_with_retries(
                            replica_info.stub.Ping, 
                            empty_pb2.Empty(),
                            timeout=5,
                            num_attempts=2,
                            delay_seconds=1
                        )
                if output is None:
                    dead_replica_ids.append(replica_id)
            #Mark all dead replicas
            if dead_replica_ids:
                async with replica_lock:
                    for r_id_dead in dead_replica_ids:
                        if r_id_dead in replica_registry:
                            print(f"[WorkerManager-{self.worker_id}] Updating status to 'dead' for replica_id: {r_id_dead} in registry.")
                            replica_registry[r_id_dead].status = "dead"
            
            await asyncio.sleep(configurations.scheduler_replica_heartbeat_interval_seconds)




async def serve(node_port, node_id, head_address, head_port):
    server = grpc.aio.server()
    # Create a head store client instance
    hsclient = HeadStoreClient(head_address, head_port)
    
    # Instantiate managers
    # Pass node_id to WorkerManager if it needs it for context (e.g. logging)
    worker_manager_instance = WorkerManager(node_id=node_id, hs_client_instance=hsclient) 
    head_node_manager_instance = HeadNodeManager(
        node_id=node_id, 
        node_address="localhost", # Assuming scheduler runs on localhost relative to its replicas
        node_port=node_port, 
        head_address=head_address, 
        head_port=head_port,
        hs_client_instance=hsclient 
    )

    worker_service_pb2_grpc.add_WorkerServiceServicer_to_server(worker_manager_instance, server)
   
    headnode_service_pb2_grpc.add_HeadNodeServiceServicer_to_server(head_node_manager_instance, server)
    #await asyncio.sleep(3)
    
    server.add_insecure_port(f"[::]:{node_port}")
    print(f"[Scheduler-{node_id}] Server listening on port {node_port}")
    await server.start()
    

    # Start background tasks using the specific instances
    task1 = asyncio.create_task(worker_manager_instance.start_heartbeat_loop(), name=f"WorkerHeartbeatLoop-{node_id}")
    task2 = asyncio.create_task(head_node_manager_instance._send_health_updates(), name=f"HeadNodeHealthUpdates-{node_id}")
    # Keep track of tasks if more sophisticated shutdown is needed later (e.g., cancelling them)
   
    
   
    #Free the thread
    
    await server.wait_for_termination()

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--node_id", type=int, required=True)
    parser.add_argument("--port", type=str, required=True)
    parser.add_argument("--head_address", type=str, required=True)
    args = parser.parse_args()
    node_port = 50051
    
    _register_node(args.node_id, "localhost", node_port, args.head_address, args.port)
    await serve(node_port, args.node_id, args.head_address, args.port)
    

asyncio.run(main())
