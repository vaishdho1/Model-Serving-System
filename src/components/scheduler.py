from concurrent import futures
import grpc
from src.generated import headnode_service_pb2, worker_service_pb2, worker_service_pb2_grpc, headnode_service_pb2_grpc, replica_service_pb2, replica_service_pb2_grpc, common_pb2
import torch
import multiprocessing
import grpc
from dataclasses import dataclass
from concurrent import futures
import subprocess
import time
import os

import argparse
from src.lib import configurations, FutureManager, HeadStoreClient, Replica, CompositeReplica
from src.lib.helpers import try_send_with_retries, try_send_with_retries_sync, send_with_delay
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

    async def StartReplica(self,replica_id,replica_port, deployment_name, deployment_id):
        
        async with replica_lock:
            if replica_id in replica_registry:
                print(f"[Scheduler-{self.worker_id}] Changing the status to dead for replica_id: {replica_id}")
                replica_registry[replica_id].status = "DEAD"
                
        
        
        metrics_port = 9000+ replica_id

        async with self.gpu_lock:
            cmd = [
                    "python3", "-m", "src.components.add_replica_vllm", 
                    "--replica_id", str(replica_id), 
                    "--num_cpus", str(1), 
                    "--num_gpus", str(1), 
                    "--parent_port", str(self.node_port),  
                    "--port", str(replica_port),           # Port for the new replica's server
                    "--deployment_name", str(deployment_name),
                    "--deployment_id", str(deployment_id),  # What deployment is this replica a part of
                    "--metrics_port", str(metrics_port),
                    
                ]
            

            print(f"[Scheduler-{self.worker_id}] Starting replica process for ID {replica_id} with command: {' '.join(cmd)}")
                
            try:
                    
                    log_file_name = f"replica_{replica_id}.log"
                    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                    with open(log_file_name, "w") as log_file:
                        #I want the process id of the subprocess
                        subprocess.Popen(
                            cmd, 
                            stdout=log_file, 
                            stderr=log_file, 
                            cwd=project_root,
                            env=dict(os.environ, PYTHONUNBUFFERED="1")  # Disable Python output buffering
                        )
                        
            except Exception as e:
                    print(f"[Scheduler-{self.worker_id}] Error starting replica process for ID {replica_id}: {e}")
                    replica_futures.set_result(replica_id, False)
                    raise e
        #Return success for the logical replica
        
        print(f"[Scheduler-{self.worker_id}] Replica process for ID {replica_id} initiated. Waiting for its registration...")
        return True
    # In your HeadNodeManager class (scheduler.py)

    async def CreateReplica(self, request, context):
        global replica_num
        replica_id = -1 # To store the ID generated under lock
        replica_list = []


        

        # Create the composite object to hold the children
        #async with replica_lock:
        #replica_registry[replica_id] = CompositeReplica(replica_id)

        # --- NEW SEQUENTIAL STARTUP LOGIC ---
        try:
            # Start each child process one by one
            for i in range(2): # Loop to start 2 replicas
                async with replica_lock: 
                    replica_num += 1
                    replica_id = replica_num # This is the logical replica id
                    replica_port = 50100 + (replica_id % 1000)  
                print(f"[Scheduler] Starting child replica {replica_id}...")
            
                # Use a future to wait for this specific child's registration
                registration_future = replica_futures.create_future(replica_id)
            
                # Start the subprocess, but don't wait for the process itself
                
                await self.StartReplica(replica_id, replica_port, request.deployment_name, request.deployment_id)
                # Wait for the gRPC registration to complete before starting the next one
                await asyncio.wait_for(registration_future, timeout=60.0) 
                print(f"[Scheduler] Child replica {replica_id} successfully registered.")
                #Adds the replica ids which are created to the list
                replica_list.append(worker_service_pb2.ReplicaContent(replica_id=replica_id, port=str(replica_port)))
        except Exception as e:
            print(f"[Scheduler] ERROR during sequential startup: {e}")
            # Handle cleanup and return an error
            return worker_service_pb2.ReplicaCreationReply(worker_id=self.worker_id, replicas=[], created=0)

        print(f"[Scheduler] All 3 child replicas for {replica_id} are up.")
        # Return success for the logical replica
        print(f"[Scheduler] Replica list: {replica_list}")
        return  worker_service_pb2.ReplicaCreationReply(worker_id=self.worker_id,worker_address=self.node_address, replicas=replica_list, created=1)
    
   
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
        
        
        worker_service_stub = replica_service_pb2_grpc.WorkerServiceStub(grpc.aio.insecure_channel(f"0.0.0.0:{request.port}"))
        
        print(f"[WorkerManager-{self.worker_id}] Registering replica_id: {replica_id} (PID: {pid}) with port: {request.port} and state: {request.state}")
        
        # Fix the parameter order
        replica_handle = Replica(
            pid=pid,
            replica_id=replica_id,
            worker_id=self.worker_id,        # ✅ Move worker_id to correct position  
            stub=worker_service_stub,        # ✅ Move stub to correct position
            headnode_stub=self._hcstub,      # ✅ Move headnode_stub to correct position
            deployment_id=request.deployment_id,  # ✅ Move deployment_id to end
            port = request.port
        )
        async with replica_lock:
            replica_registry[replica_id] = replica_handle
        #This will only set if the future exists
        replica_futures.set_result(replica_id,True)
        return worker_service_pb2.Reply(ack=1)
    
    
    '''
    async def sendHealthupdate(self, request, context):
       
        
        async with replica_lock:
            replica_info = replica_registry.get(request.replica_id)
        #Incase the dead replicas are sending health updates, 
        if replica_info is None or replica_info.status == "DEAD": 
            #print(f"[WorkerManager-{self.worker_id}] Replica {request.replica_id} not found or dead. Sending NACK.")
            return worker_service_pb2.HealthReply(ack=False)
        else:
                #print(f"[WorkerManager-{self.worker_id}] Replica {request.replica_id} is healthy. Sending ACK.")
                return worker_service_pb2.HealthReply(ack=True)
    '''
    
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
                    asyncio.createTask(self.StartReplica(replica_id, replica_info.deployment_id, replica_info.deployment_name))
           
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
    #task1 = asyncio.create_task(head_node_manager_instance.start_heartbeat_loop(), name=f"WorkerHeartbeatLoop-{node_id}")
    # Enable health updates to HeadController - this was commented out!
    #task2 = asyncio.create_task(head_node_manager_instance._send_health_updates(), name=f"HeadNodeHealthUpdates-{node_id}")
    # Keep track of tasks if more sophisticated shutdown is needed later
   
    
   
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
