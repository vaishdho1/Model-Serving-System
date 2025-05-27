'''
This is the main serve controller that is used for 
autoscaling replicas
starting the http proxy and making sure its running
Sending deployment changes to the proxy.
This is where your health checks come.

'''
from src.generated import headnode_service_pb2, headnode_service_pb2_grpc
import subprocess
from src.lib import ProxyManager, DeploymentManager, AutoScaleManager, HealthManager
import asyncio
import grpc 
from typing import Optional


class HeadController(
    headnode_service_pb2_grpc.WorkerManagementServiceServicer,
    headnode_service_pb2_grpc.ProxyManagementServiceServicer
):

    def __init__(self):
        self.http_port = 8000
        self.grpc_port = 50051 # Proxy's gRPC port for ProxyManager to ping
        self.node_port = 50054 # HeadController's own gRPC port
        
        self.proxy_manager = ProxyManager(self.node_port, self.http_port, self.grpc_port)
        self.deployment_manager = DeploymentManager()   
        self.health_manager = HealthManager()
        self.auto_scale_manager = AutoScaleManager() # Ensure this class is defined and imported
         
        # Shared variable for the latest routing table snapshot
        self._latest_routing_snapshot: Optional[headnode_service_pb2.RoutingUpdate] = None
        self._routing_snapshot_lock = asyncio.Lock() # To protect concurrent access

        # Event to signal that _latest_routing_snapshot has been updated
        self._routing_update_event = asyncio.Event()

    
        

    async def _on_deployment_change(self):
        """Call this method after any change in DeploymentManager affects routing."""
        print("[HeadController] A deployment change occurred, generating new routing snapshot.")
        new_snapshot = await self.deployment_manager.get_current_routing_table()
        async with self._routing_snapshot_lock: # Use consistent lock name
            self._latest_routing_snapshot = new_snapshot # Use consistent variable name
        
        self._routing_update_event.set()  # Signal subscribers
        self._routing_update_event.clear() # Reset for next signal
        print(f"[HeadController] Published new routing snapshot (ts: {new_snapshot.timestamp_ns if new_snapshot else 'N/A'}). Event processed.")

    # --- ProxyManagementServiceServicer RPCs ---
    async def SubscribeToRoutingUpdates(self, 
                                        request: headnode_service_pb2.SubscriptionRequest, 
                                        context: grpc.aio.ServicerContext):
        proxy_id = request.proxy_id if request.proxy_id else "Unknown Proxy"
        print(f"[HeadController] Proxy '{proxy_id}' subscribed for routing updates.")
        
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
            if context.is_active():
                await context.abort(grpc.StatusCode.INTERNAL, f"Error sending initial snapshot: {str(e)}")
            return # Terminate this specific stream

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
            if context.is_active():
                 await context.abort(grpc.StatusCode.INTERNAL, f"Error in routing update stream: {str(e)}")
        finally:
            print(f"[HeadController] Subscription stream for proxy '{proxy_id}' ended.")

    

    # --- WorkerManagementServiceServicer RPCs ---
   

    async def RecordMetrics(self, request: headnode_service_pb2.MetricsRequest, context):
        #Send the metrics to the autoscaler
        await self.auto_scale_manager.load_metrics(request)
        return headnode_service_pb2.MetricsReply(acknowledge=True)

   
    # Worker node calls this to register with the head node
    async def RegisterNode(self, request: headnode_service_pb2.RegisterRequest, context):
        print(f"[HeadController] RegisterNode called by node {request.node_id} at {request.node_address}:{request.port}.")
       
        await self.deployment_manager.add_or_update_deployment(request.node_id, request.node_address, request.port, request.state)
        
        return headnode_service_pb2.RegisterReply(ack=True)

    