from src.generated import headnode_service_pb2
import asyncio
from src.lib.configurations import *
class HealthManager:
    def __init__(self, deployment_manager, node_info_cache):
        self.deployment_manager = deployment_manager
        self.node_info_cache = node_info_cache
        asyncio.create_task(self.ping_workers())
       
    async def SendHealthStatus(self, request: headnode_service_pb2.HealthStatusUpdate, context):
        print(f"HealthManager: Received health status update for worker {request.worker_id} with state {request.state}")
       
        # Simulating a change that requires routing update
        worker_id = request.worker_id
        deployment_id = request.deployment_id
        change_detected = False
        for replica_id, status in request.replica_states:
            if status == "DEAD":
               
                change_detected = True
                 #This takes care of the auto scale manager and node info cache
                await self.deployment_manager.remove_replica_from_deployment(deployment_id, replica_id, worker_id)
        #If there is a change in the deployment, we need to update the routing table
        if change_detected:
            await self._on_deployment_change() 
        # await self._on_deployment_change() 
        return headnode_service_pb2.HealthStatusReply(ack=True, isAlive="true") # Assuming head node always says worker is alive for now

    async def ping_workers(self):
        while True:
            nodes = await self.node_info_cache.get_all_nodes()
            is_alive = True
            for node in nodes:
                try:
                    # Use the existing stub to call Ping
                    response = await node.worker_stub.Ping()
                    # Optionally, handle the response (e.g., check if acknowledged)
                    if not response.acknowledged:
                        alive = False
                        print(f"Node {node.node_address} did not acknowledge ping.")
                except Exception as e:
                    alive = False
                if not is_alive:
                    #Search for all the replicas in this node,
                   # remove them from the deployment manager and node info cache
                   # Start these replicas elsewhere
                    pass
            await asyncio.sleep(worker_ping_interval)  # Ping interval







       
