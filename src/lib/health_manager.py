from src.generated import headnode_service_pb2
import asyncio
from src.lib.configurations import *
from google.protobuf.empty_pb2 import Empty
from src.lib.logging_config import health_logger
class HealthManager:
    def __init__(self, head_controller):
        self.head_controller = head_controller
        asyncio.create_task(self.ping_workers())
       
    async def SendHealthStatus(self, request: headnode_service_pb2.HealthStatusUpdate, context):
        health_logger.debug(f"[HealthManager] Received health status update for worker {request.worker_id}")
       
        # Simulating a change that requires routing update
        worker_id = request.worker_id
        worker_address = request.worker_address
        worker_port = request.port
        address = f"{worker_address}:{worker_port}"
        change_detected = False
        for replica_state in request.replica_states:
            print(f"[HealthManager] Replica state: {replica_state}")
            if replica_state.status == "DEAD":
                change_detected = True
                # This takes care of the auto scale manager and node info cache
                await self.head_controller.deployment_manager.remove_replica_from_deployment(replica_state.deployment_id, replica_state.replica_id, worker_id)
                #Will not be doing this anymore as the scheduler will handle this
                #await self.head_controller.replica_queue.put((address,replica_state.deployment_id))
                
        #If there is a change in the deployment, we need to update the routing table
        if change_detected:
            await self.head_controller._on_deployment_change() 
        # await self._on_deployment_change() 
        return headnode_service_pb2.HealthStatusReply(ack=True, isAlive="true") # Assuming head node always says worker is alive for now

    async def ping_workers(self):
        while True:
            nodes = await self.head_controller.node_info_cache.get_all_nodes()
            is_alive = True
            for node in nodes:
                try:
                    # Use the existing stub to call Ping
                    response = await node.worker_stub.Ping(Empty())
                    # Optionally, handle the response (e.g., check if acknowledged)
                    if not response.acknowledged:
                        alive = False
                        health_logger.warning(f"[HealthManager] Node {node.node_address} did not acknowledge ping.")
                except Exception as e:
                    health_logger.error(f"[HealthManager] Error pinging node {node.node_address}: {e}")
                    alive = False
                if not is_alive:
                    '''
                    Todo:
                    Search for all the replicas in this node,
                    remove them from the deployment manager and node info cache
                    Start these replicas elsewhere
                   '''
                    pass
            await asyncio.sleep(worker_ping_interval)  # Ping interval







       
