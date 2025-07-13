'''
This is the main serve controller that is used for 
autoscaling replicas
starting the http proxy and making sure its running
Sending deployment changes to the proxy.
This is where your health checks come.

'''
from src.generated import headnode_service_pb2, headnode_service_pb2_grpc, worker_service_pb2_grpc, worker_service_pb2
import subprocess
from src.lib import ProxyManager, DeploymentManager, HealthManager, AutoScaleManager, NodeInfo, AWSVMManager
import asyncio
import grpc 
from typing import Optional
from src.lib.helpers import try_send_with_retries, get_gcp_internal_ip, get_aws_internal_ip
from src.lib.utils import get_local_ip
import argparse
from concurrent import futures
import threading

class HeadController(
    headnode_service_pb2_grpc.WorkerManagementServiceServicer,
    headnode_service_pb2_grpc.ProxyManagementServiceServicer
):

    def __init__(self, http_port, node_port, grpc_port, host_address="localhost"):  
        self.http_port = http_port
        self.node_port = node_port
        self.grpc_port = grpc_port
        self.host_address = host_address
        self.head_node_address = f"{host_address}:{self.node_port}"
        self.proxy_manager = ProxyManager(self.node_port, self.http_port, self.grpc_port)
        self.node_info_cache = NodeInfo()
        self.auto_scale_manager = AutoScaleManager()
        # Sending autoscale manager to run autoscaling within deployment manager
        self.deployment_manager = DeploymentManager(self.node_info_cache, self.auto_scale_manager)   
        #This queue holds information about the replicas that need to be created with the addresses of the workers
        self.replica_queue = asyncio.Queue()
        #This queue holds information about the replicas that need to be assigned to a worker
        self.pending_replicas = asyncio.Queue()
        #Start the replica creation task to run in the background
        #self.vm_manager = VMManager("data-backup-457517-f5", "us-east1-d")
        #Currently using AWSVMManager for AWS
        self.vm_manager = AWSVMManager("us-east-1")
        #Todo: See if this can be made better
        asyncio.create_task(self.replica_creation())
        
       
        
        
        #self.deployment_scheduler = DeploymentScheduler(self)
        self.create_deployments()
        #Need to call this in a thread, as VM creation is a blocking operation
        asyncio.create_task(self._create_vm_in_thread())
        
        self.health_manager = HealthManager(self)
        
        
        self._node_map = {}
        # Todo: Need to add autoscale manager here
        #self.auto_scale_manager = AutoScaleManager() 
         
        # Shared variable for the latest routing table snapshot
        self._latest_routing_snapshot: Optional[headnode_service_pb2.RoutingUpdate] = None
        self._routing_snapshot_lock = asyncio.Lock() # To protect concurrent access

        # Event to signal that _latest_routing_snapshot has been updated
        self._routing_update_event = asyncio.Event()

    def create_deployments(self):
        
        self.deployment_manager.add_or_update_deployment(deployment_id = 1, name = "/v1/chat/gpt2", version = "1.0", num_cpus = 2, num_gpus = 1)
        
        self.deployment_manager.add_or_update_deployment(deployment_id = 2, name = "/v1/chat/tinyllama", version = "1.0", num_cpus = 2, num_gpus = 1)
       
        self.deployment_manager.add_or_update_deployment(deployment_id = 3, name = "/v1/chat/phi2", version = "1.0", num_cpus = 2, num_gpus = 1)

        

    async def _on_deployment_change(self):
        """Call this method after any change in DeploymentManager affects routing."""
        print("[HeadController] A deployment change occurred, generating new routing snapshot.")
        new_snapshot = await self.deployment_manager.get_current_routing_table()
        async with self._routing_snapshot_lock:
            self._latest_routing_snapshot = new_snapshot 
        
        self._routing_update_event.set()  # Signal subscribers

        self._routing_update_event.clear() # Reset for next signal
        print(f"[HeadController] Published new routing snapshot (ts: {new_snapshot.timestamp_ns if new_snapshot else 'N/A'}). Event processed.")

    # --- ProxyManagementServiceServicer RPCs ---
    async def SubscribeToRoutingUpdates(self, 
                                        request: headnode_service_pb2.SubscriptionRequest, 
                                        context: grpc.aio.ServicerContext):
        proxy_id = request.proxy_id if request.proxy_id else "Unknown Proxy"
        print(f"[HeadController] Proxy  subscribed for routing updates.")
        #Start the heartbeat task of the proxy
        asyncio.create_task(self.proxy_manager.send_heartbeat())
        last_yielded_timestamp_ns = 0 
        try:
            initial_snapshot = await self.deployment_manager.get_current_routing_table()
            async with self._routing_snapshot_lock:
                self._latest_routing_snapshot = initial_snapshot
            if initial_snapshot:
                print(f"[HeadController] Sending initial snapshot (ts: {initial_snapshot.timestamp_ns}) to proxy '{proxy_id}'.")
                yield initial_snapshot
                last_yielded_timestamp_ns = initial_snapshot.timestamp_ns
            else:
                print(f"[HeadController] No initial snapshot currently available for proxy '{proxy_id}'. Waiting for first update event.")
        
        except Exception as e:
            print(f"[HeadController] Error sending initial snapshot to proxy '{proxy_id}': {e}")
            return

        # 2. Loop to wait for new updates and send them
        try:
            while True:
                await self._routing_update_event.wait() # Wait until .set() is called

                async with self._routing_snapshot_lock: # Corrected: Read the shared snapshot
                    new_snapshot = self._latest_routing_snapshot 
                
                # Crucial check: only send if new_snapshot exists and is newer than what this proxy last got
                if new_snapshot and new_snapshot.timestamp_ns > last_yielded_timestamp_ns:
                    print(f"[HeadController] Sending updated snapshot (ts: {new_snapshot.timestamp_ns}) to proxy '{proxy_id}'. Last sent ts: {last_yielded_timestamp_ns}.")
                    yield new_snapshot
                    last_yielded_timestamp_ns = new_snapshot.timestamp_ns
                
                # Else, this proxy already has this state or newer; or snapshot is None (should not happen if event set for valid state)
                
        except asyncio.CancelledError:
            
            print(f"[HeadController] Subscription for proxy '{proxy_id}' cancelled (client disconnected or server shutdown).")
        except Exception as e:
            print(f"[HeadController] Error in routing update stream for proxy '{proxy_id}': {e}")
           
        finally:
            print(f"[HeadController] Subscription stream for proxy '{proxy_id}' ended.")

    

    # --- WorkerManagementServiceServicer RPCs ---
    
    async def SendHealthStatus(self, request: headnode_service_pb2.HealthStatusUpdate, context):
        print(f"[HeadController] Received health status update from worker {request.worker_id}")
        # Delegate to health manager
        return await self.health_manager.SendHealthStatus(request, context)

    async def RecordMetrics(self, request: headnode_service_pb2.MetricsRequest, context):
        #Send the metrics to the autoscaler
        try: 
            await self.auto_scale_manager.load_metrics(request)
            return headnode_service_pb2.MetricsReply(acknowledge=True)
        except Exception as e:
            print(f"[HeadController] Error recording metrics: {e}")
            return headnode_service_pb2.MetricsReply(acknowledge=False)

   
    # Worker node calls this to register with the head node
    async def RegisterNode(self, request: headnode_service_pb2.RegisterRequest, context):
        print(f"[HeadController] RegisterNode called by node {request.node_id} at {request.node_address}:{request.port}.")
        #Add a new node into the cache
        await self.node_info_cache.add_node(request)
        #Not sending update to the proxy yet- Need to create a replica
       
        worker_address = f"{request.node_address}:{request.port}"
        await self.replica_queue.put((worker_address, 2))
        #Directly calling creation of replica here
        #await self.create_replica(worker_address, 2)
        #await self.replica_queue.put((worker_address, 3))
        #asyncio.create_task(self.replica_creation(worker_address))
        return headnode_service_pb2.RegisterReply(ack=True)
    
    async def replica_creation(self):
        #Checks the queue for any replicas that need to be created
        print(f"[HeadController] Starting replica creation task")
        while True:
            try:
                replica_info = await self.replica_queue.get()
                #Waiting for the node to start up, this is a hack to make sure the node is ready to receive requests
                await asyncio.sleep(3)
                 
                
                #This should never happen, if it does, need to fix it
                if not isinstance(replica_info, tuple) or len(replica_info) != 2:
                    print(f"[HeadController] Error: Invalid replica_info format: {replica_info}")
                    continue

                address, deployment_id = replica_info
                print(f"[HeadController] Spawning creation task for deployment {deployment_id} on {address}")
                asyncio.create_task(self.create_replica(address, deployment_id))
                # Mark the queue item as processed so the queue knows we've handled it.
                self.replica_queue.task_done()
            except Exception as e:
                print(f"[HeadController] Error in replica creation loop: {e}")
                # Continue the loop even if there's an error
                continue

    async def create_replica(self, address:str,deployment_id:int, _num_cpus = 0, _num_gpus = 0):

        stub = worker_service_pb2_grpc.HeadNodeServiceStub(grpc.aio.insecure_channel(address))
        
        
        deployment = await self.deployment_manager.get_deployment(deployment_id)
        if not deployment:
            print(f"[HeadController] Error: Deployment {deployment_id} not found")
            return None
        print(f"[HeadController] Requesting to create replica for deployment {deployment_id} with name {deployment.deployment_name}")
        request = worker_service_pb2.ReplicaCreationRequest(base_node_address = self.head_node_address,
                                                          deployment_id = int(deployment_id),
                                                          num_cpus = _num_cpus,
                                                          num_gpus = _num_gpus,
                                                          deployment_name = deployment.deployment_name)
        #Starting the replica to run
        #await self.deployment_manager.add_replica_to_deployment(deployment_id, replica_num = response.replica_id, worker_id = response.worker_id, worker_address = address)
        try:
            response = await try_send_with_retries(stub.CreateReplica, request, num_attempts=3, delay_seconds=2)
            # Add replica to the deployment manager and update the routing table
           
            if response.created:
                print(f"[HeadController] Adding replica to deployment {deployment_id}")
                await self.deployment_manager.add_replica_to_deployment(
                    deployment_id, 
                    str(response.worker_id), 
                    #Todo: Code for this
                    replicas = response.replicas, 
                    num_cpus = _num_cpus,
                    num_gpus = _num_gpus,
                    worker_address = response.worker_address
                )
                print(f"[HeadController] Deployment manager updated")
                await self._on_deployment_change()
            return response
        except Exception as e:
            
            #Add this replica in a queue to be created later currently this can run forever
            #Todo: but we can add a timeout to the request to be created later.
            print(f"[HeadController] Error creating replica for deployment {deployment_id}: Will retry later")
            await self.pending_replicas.put((deployment_id))
            return None
        

    
    async def _create_vm_in_thread(self):
        """Run VM creation in a separate thread using asyncio.to_thread."""
        for i in range(4):
            try:
                print(f"[HeadController] Creating VM {i+1}")
                await asyncio.to_thread(
                    self.vm_manager.create_vm,
                    scheduler_id=i+1,
                    name=f"scheduler-{i+1}",
                    model_id="small",
                    head_controller_address=self.host_address,
                    head_controller_port=self.node_port
                )
            except Exception as e:
                print(f"[HeadController] Error creating VM in thread: {e}")
            await asyncio.sleep(5)
       

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--http_port", type=int, required=True)
    parser.add_argument("--node_port", type=int, required=True)
    parser.add_argument("--grpc_port", type=int, required=True)

   
    args = parser.parse_args()
    host_address = get_aws_internal_ip() 
    #host_address =get_local_ip()
    head_controller_instance = HeadController(args.http_port, args.node_port, args.grpc_port, host_address)
   
    server = grpc.aio.server()
    headnode_service_pb2_grpc.add_WorkerManagementServiceServicer_to_server(
        head_controller_instance, server
    )
    headnode_service_pb2_grpc.add_ProxyManagementServiceServicer_to_server(
        head_controller_instance, server
    )
    
    server.add_insecure_port(f"0.0.0.0:{args.node_port}")
    await server.start()
    print(f"HeadController listening on port {args.node_port}")
    await server.wait_for_termination()



if __name__ == "__main__":
    asyncio.run(main())