from concurrent import futures
import grpc
from src.generated import headnode_service_pb2, worker_service_pb2, worker_service_pb2_grpc, headnode_service_pb2_grpc, replica_service_pb2_grpc, common_pb2
import torch
import grpc
import subprocess
import time
import os


from src.lib import configurations, FutureManager, Replica
from src.lib.helpers import try_send_with_retries, try_send_with_retries_sync
import signal
import asyncio
from google.protobuf import empty_pb2
from src.lib.utils import get_local_ip
replica_lock = asyncio.Lock()
'''
This is the code of a general worker node scheduler.
When a worker node is started it registers with the head node and then starts a health monitor thread.
'''
node_id = 1

replica_num = 0
#This is a global registry of all the replicas
replica_registry = {}
# Create a replica futures to return requests to the head node
replica_futures = FutureManager()




def _register_node(worker_id, node_address, node_port, head_address, head_port, num_cpus, num_gpus):
        # Register the node with the head node
        print(f"[Scheduler-{worker_id}] Registering node...")
        
        
        node_resource = headnode_service_pb2.Resource(
            num_cpus=int(num_cpus),  # Default CPU allocation
            num_gpus=int(num_gpus)  # Default GPU allocation
        )
        
        request_msg = headnode_service_pb2.RegisterRequest(
            node_id = int(worker_id),
            node_address = str(node_address),
            port = str(node_port),
            state = "alive",
            resource = node_resource  # Add the resource field
        )

        max_retries = getattr(configurations, 'head_store_max_retries', 3)
        retry_delay = getattr(configurations, 'head_store_retry_delay', 2)
        timeout_duration = getattr(configurations, 'head_store_timeout', 5) # Timeout for the RPC call itself
        registration_successful = False

        try:
            with grpc.insecure_channel(f"{head_address}:{head_port}") as channel:
                stub = headnode_service_pb2_grpc.WorkerManagementServiceStub(channel)
                response = try_send_with_retries_sync(
                    stub.RegisterNode,
                request =request_msg,
                num_attempts=max_retries,
                delay_seconds=retry_delay,
                timeout=timeout_duration,
            )
            if response and response.ack:
                print(f"[Scheduler-{worker_id}] Node successfully registered. Ack: {response.ack}")
                #Send backt he http port
            elif isinstance(response, Exception):
                print(f"[Scheduler-{worker_id}] Error during registration attempt: {response}")
                #Kill the scheduler
                os.kill(os.getpid(), signal.SIGTERM)
                return
            else:
                print(f"[Scheduler-{worker_id}] Registration failed. Ack: {response.ack}")
        except Exception as e:
            print(f"[Scheduler-{worker_id}] Error during registration attempt: {e}")
            #Kill the scheduler
            os.kill(os.getpid(), signal.SIGTERM)
            return
        
    
class HeadNodeManager(worker_service_pb2_grpc.HeadNodeServiceServicer, worker_service_pb2_grpc.ReplicaServiceServicer):
    def __init__(self, node_id, node_address, node_port, head_address, head_port):
        self.worker_id = node_id
        self.channel = grpc.aio.insecure_channel(f"{head_address}:{head_port}")
        self._hcstub = headnode_service_pb2_grpc.WorkerManagementServiceStub(self.channel)
        #self.hsclient = hs_client_instance # Store the passed hsclient
        self.node_address = node_address
        self.node_port = node_port 
        self.head_address = head_address
        self.head_port = head_port  
        self.need_cleanup = False
        #Assume there is a single gpu for now
        self.gpu_lock  = asyncio.Lock()
        
       
        # Send regular health updates as a separate thread
    
    async def cleanup_replicas(self):
        global replica_registry
       
        async with replica_lock:
           
            print(f"[Scheduler-{self.worker_id}] Starting replica cleanup...")
            #print(f"[Scheduler-{self.worker_id}] Replica registry before cleanup: {[id for id in replica_registry]}")
            initial_count = len(replica_registry)
            replica_registry = { 
                replica_id: rinfo for replica_id, rinfo in replica_registry.items() 
                if rinfo.status != "DEAD" 
            }
            final_count = len(replica_registry)
        print(f"[Scheduler-{self.worker_id}] Replica cleanup complete. Removed {initial_count - final_count} dead replicas.")

    async def send_kill_signal(self):
        #Kill all replicas and the scheduler
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
            print(f"[Scheduler-{self.worker_id}] Sending health updates")
            current_replica_states = []
            # Cleanup any dead replicas
            
            async with replica_lock:
                current_replica_state = list(replica_registry.items())
            
            replica_state_pbs_list = []
            try:
                #Added deployment_id to send to health checks
                replica_state_pbs_list = [ 
                    headnode_service_pb2.ReplicaState(
                        replica_id=replica_id, 
                        replica_port= str(values.port),
                        status=values.status if hasattr(values, 'status') else "unknown", # Defensive access
                        deployment_id=values.deployment_id if hasattr(values, 'deployment_id') else "unknown"
                    ) for replica_id, values in current_replica_state
                ]
            except Exception as e_comp:
                print(f"[Scheduler-{self.worker_id}] CRITICAL ERROR: Exception during replica_state list comprehension: {e_comp}")
               
            print(f"[Scheduler-{self.worker_id}] Attempting to send health report for node {self.worker_id} with {len(replica_state_pbs_list)} replica states...")
            output = await try_send_with_retries(
                    self._hcstub.SendHealthStatus, 
                    request = headnode_service_pb2.HealthStatusUpdate(
                        worker_id=self.worker_id, 
                        worker_address=self.node_address,
                        replica_states=replica_state_pbs_list
                    ),
                    num_attempts= 3, 
                    delay_seconds= 2 
            )
            print(f"[Scheduler-{self.worker_id}] Health update output: {output}")
            print(f"[Scheduler-{self.worker_id}] Health update output type: {type(output)}")
            
            # Check if output is an exception (which means the call failed)
            if isinstance(output, Exception):
                print(f"[Scheduler-{self.worker_id}] Health update failed with exception: {output}")
                #print(f"[Scheduler-{self.worker_id}] Exception type: {type(output)}")
                await self.send_kill_signal()
                return
            
            if output is None or output.ack == 0:
                    print(f"[Scheduler-{self.worker_id}] Head node reported scheduler (node_id: {self.worker_id}) as unhealthy (ack=0). Initiating shutdown...")
                    await self.send_kill_signal()
                    return # Exit thread
            # Moved this here: Update the replica registry with status here since the headNode must know about the dead replicas
            await self.cleanup_replicas()
            #print(f"[Scheduler-{self.worker_id}] Health update cycle complete. Output: {output}. Sleeping for {configurations.scheduler_health_update_interval}s.")
            await asyncio.sleep(configurations.scheduler_health_update_interval) 

    

    async def StartReplicaCpp(self, replica_id, replica_port, deployment_name, deployment_id):
        # The executable is installed in a standard system location by our Dockerfile.
        
        cpp_executable_path = "/usr/local/bin/replica_server"
        metrics_port = 9000+ replica_id

        # Command to run the C++ binary with its arguments
        cmd = [
            cpp_executable_path,
            "--port", str(replica_port),
        "--replica_id", str(replica_id),
        "--parent_port", str(self.node_port),
        "--deployment_name", str(deployment_name),
        "--deployment_id", str(deployment_id),
        "--metrics_port", str(metrics_port),
        "--num_cpus", str(1),
        "--num_gpus", str(1),
                ]


       
        #Todo: Implement cuda availability for replicas here

        print(f"[Scheduler-{self.worker_id}] Starting replica process for ID {replica_id} with command: {' '.join(cmd)}")
        
        try:
            
            log_file_name = f"replica_{replica_id}.log"
            #print(f"[Scheduler-{self.worker_id}] Redirecting output of replica {replica_id} to {log_file_name}")
            
          
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            #print(f"[Scheduler-{self.worker_id}] Setting working directory to: {project_root}")
            
            log_file = open(log_file_name, "w")
           
            subprocess.Popen(
                cmd, 
                stdout=log_file, 
                stderr=log_file, 
                cwd=project_root,
                env=dict(os.environ, PYTHONUNBUFFERED="1")  # Disable Python output buffering
            )
        except Exception as e:
            raise e
            
    async def CreateReplica(self, request, context):
        global replica_num
        replica_id = -1 # To store the ID generated under lock

        async with replica_lock: 
            replica_num += 1
            replica_id = replica_num
            replica_port = 50100+ replica_id
        try:
            await self.StartReplicaCpp(replica_id, replica_port, request.deployment_name, request.deployment_id)
        except Exception as e:
            print(f"[Scheduler-{self.worker_id}] Failed to start replica process for ID {replica_id}: {e}")
            
            error_reply = worker_service_pb2.ReplicaCreationReply(
                worker_id=self.worker_id, 
                worker_address=self.node_address,
                replicas=[worker_service_pb2.ReplicaContent(replica_id=replica_id, port=str(replica_port))],
                created=False 
                
            )
            replica_futures.set_result(replica_id, error_reply)
            return error_reply # Return the error reply directly to the gRPC client

        print(f"[Scheduler-{self.worker_id}] Replica process for ID {replica_id} initiated. Waiting for its registration...")
        fut = replica_futures.create_future(replica_id)
        return await fut # This will wait for WorkerManager.RegisterReplica to call replica_futures.set_result
    
   
    #Ping from the head node to the scheduler
    async def Ping(self, request, context):
        #time in hour:minute:second format
        print(f"[Scheduler-{self.worker_id}] Received ping from head node : {time.strftime('%H:%M:%S', time.localtime())}")
        return common_pb2.Ack(acknowledged=True)    
    
    
    
    # ------------------------------------Replica Services-------------------------------------------------
    
    async def RegisterReplica(self, request, context):

        '''
        Once a replica registers, a stub is created to it and stored along with other information
        '''
        #This is a string
        replica_id = request.replica_id
        pid = request.pid
        
        
        async with replica_lock:
            if replica_id in replica_registry:
                print(f"[WorkerManager-{self.worker_id}] Replica {replica_id} is already registered, skipping duplicate registration")
                return worker_service_pb2.Reply(ack=1)
        
        # Create stubs to communicate with the replica
        
        # WorkerServiceStub for task processing (PushTask)
        worker_service_stub = replica_service_pb2_grpc.WorkerServiceStub(grpc.aio.insecure_channel(f"0.0.0.0:{request.port}"))
        
        print(f"[WorkerManager-{self.worker_id}] Registering replica_id: {replica_id} (PID: {pid}) with port: {request.port} and state: {request.state}")
        
        # Pass the worker_service_stub for task processing
        replica_handle  = Replica(replica_id = replica_id, port = str(request.port), pid = pid, deployment_id = request.deployment_id, worker_id = self.worker_id, stub = worker_service_stub, headnode_stub = self._hcstub)
        async with replica_lock:
            replica_registry[replica_id] = replica_handle
        
        # Returns to the create replica call which is waiting on this replica ID
        reply = worker_service_pb2.ReplicaCreationReply(worker_id=self.worker_id,worker_address=self.node_address, replicas=[worker_service_pb2.ReplicaContent(replica_id=replica_id, port=request.port)], created=1)
        replica_futures.set_result(replica_id, reply)
        #print(f"[WorkerManager-{self.worker_id}] Resolved CreateReplica future for replica_id: {replica_id}")
            
        # Acknowledgement to the replica
        return worker_service_pb2.Reply(ack=1)
    
    
    
    #This sends pings to all the replicas and if they do not respond, they are marked dead
    async def start_heartbeat_loop(self):
        while True:
            snapshot_for_ping = []
            async with replica_lock:
                snapshot_for_ping = list(replica_registry.items())

           
            for replica_id, replica_info in snapshot_for_ping:
                #Skip if the replica is already dead
                if replica_info.status == "DEAD":
                    continue
                print(f"[WorkerManager-{self.worker_id}] Pinging replica_id: {replica_id} (PID: {replica_info.pid})...")
                # Wrap the Ping call with the retry helper
                output = await try_send_with_retries(
                            replica_info.stub.Ping, 
                            empty_pb2.Empty(),
                            timeout=10,
                            num_attempts=3,
                            delay_seconds=2
                        )
                #print(f"[WorkerManager-{self.worker_id}] Ping output: {output} for replica_id: {replica_id}")
                if output is None or isinstance(output, Exception):
                    asyncio.create_task(self.StartReplicaCpp(replica_id, replica_info.port, replica_info.deployment_id, replica_info.deployment_name))
           
            await asyncio.sleep(configurations.scheduler_replica_heartbeat_interval_seconds)




async def serve(node_port, node_id, node_address, head_address, head_port):
    server = grpc.aio.server()
    
    head_node_manager_instance = HeadNodeManager(
        node_id=node_id, 
        node_address=node_address, # Assuming scheduler runs on localhost relative to its replicas
        node_port=node_port, 
        head_address=head_address, 
        head_port=head_port,
        #http_port=http_port,
        #hs_client_instance=hsclient 
    )

    worker_service_pb2_grpc.add_HeadNodeServiceServicer_to_server(head_node_manager_instance, server)
    worker_service_pb2_grpc.add_ReplicaServiceServicer_to_server(head_node_manager_instance, server)
    #headnode_service_pb2_grpc.add_HeadNodeServiceServicer_to_server(head_node_manager_instance, server)
    #await asyncio.sleep(3)
    
    server.add_insecure_port(f"0.0.0.0:{node_port}")
    print(f"[Scheduler-{node_id}] Server listening on 0.0.0.0:{node_port}")
    await server.start()
    

    # Start background tasks using the specific instances
    task1 = asyncio.create_task(head_node_manager_instance.start_heartbeat_loop(), name=f"WorkerHeartbeatLoop-{node_id}")
    # Enable health updates to HeadController - this was commented out!
    task2 = asyncio.create_task(head_node_manager_instance._send_health_updates(), name=f"HeadNodeHealthUpdates-{node_id}")
    #Keep track of tasks if more sophisticated shutdown is needed later
   
    
   
    #Free the thread
    
    await server.wait_for_termination()

async def main():
   
    #Pick variables from the environment
    
    scheduler_id = os.getenv("SCHEDULER_ID", "1")  # Default to "1" if not set
    head_port = os.getenv("HEAD_PORT")
    head_address = os.getenv("HEAD_HOST")
    num_cpus = os.getenv("NUM_CPUS", os.cpu_count())
    num_gpus = os.getenv("NUM_GPUS", torch.cuda.device_count())
    '''
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--scheduler_id", type=int, default=1)
    arg_parser.add_argument("--head_port", type=int, default=50051)
    arg_parser.add_argument("--head_address", type=str, default="localhost")
    arg_parser.add_argument("--num_cpus", type=int, default=os.cpu_count())
    arg_parser.add_argument("--num_gpus", type=int, default=torch.cuda.device_count())
    args = arg_parser.parse_args()
   '''
    
   
    node_address = get_local_ip()
    node_port = 50051
    
    #First register node with the head node this is a blocking call: Commented out for now
    print(f"[Scheduler] Starting with ID: {scheduler_id}")
    _register_node(scheduler_id, node_address, node_port, head_address, head_port, num_cpus, num_gpus)
    await serve(node_port, int(scheduler_id), node_address, head_address, head_port)
    

asyncio.run(main())
