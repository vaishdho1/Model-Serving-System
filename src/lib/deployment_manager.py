import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal

# Assuming your generated protobufs are in src.generated
from src.generated import headnode_service_pb2, worker_service_pb2
from src.lib.configurations import *

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("DeploymentManager")

ReplicaStateName = Literal["STARTING", "RUNNING", "DRAINING", "SHUTDOWN"]

@dataclass
class ReplicaInfo:
    replica_num: str  # node_id#replica_num
    worker_address: str
    state: ReplicaStateName

@dataclass
class DeploymentHandle:
    deployment_id: int
    deployment_name: str
    version: str
    num_cpus: int
    num_gpus: int
    replicas: List[ReplicaInfo] = field(default_factory=list)
    

class DeploymentManager:
    """Manages deployments and their replicas."""
    def __init__(self, node_info_cache, auto_scale_manager):
        self.deployments: Dict[int, DeploymentHandle] = {}
        self._lock = asyncio.Lock()
        self.replica_map: Dict[str, ReplicaInfo] = {}
        
        self.node_info_cache = node_info_cache
        #Currently not using autoscaling
        self.auto_scale_manager = auto_scale_manager
        #self.scheduler = deployment_scheduler
        #Start autoscaling loop
        #asyncio.create_task(self.run_autoscaling_loop())

    @staticmethod
    def _replica_id(worker_id: str, replica_num: str) -> str:
        return f"{worker_id}#{replica_num}"

    def add_or_update_deployment(self, deployment_id: int, name: str, version: str, num_cpus: int, num_gpus: int) -> DeploymentHandle:
        
        dep = self.deployments.get(deployment_id)
        if not dep:
            dep = DeploymentHandle(deployment_id, name, version, num_cpus, num_gpus)
            self.deployments[deployment_id] = dep
        else:
            dep.deployment_name = name
            dep.version = version
            dep.num_cpus = num_cpus
            dep.num_gpus = num_gpus
        return dep

    async def remove_deployment(self, deployment_id: int) -> bool:
        async with self._lock:
            dep = self.deployments.pop(deployment_id, None)
            if dep:
                for r in dep.replicas:
                    self.replica_map.pop(self._replica_id(r.worker_address, r.replica_num), None)
                return True
            logger.warning(f"Attempted to remove non-existent deployment: {deployment_id}")
            return False

    async def add_replica_to_deployment(self, deployment_id: int, worker_id: str, replica_id_num: str, worker_address: str, num_cpus: int, num_gpus: int, initial_state: ReplicaStateName = "STARTING") -> bool:
        async with self._lock:
            dep = self.deployments.get(deployment_id)
            if not dep:
                logger.error(f"Cannot add replica. Deployment {deployment_id} not found.")
                return False
            replica_info = ReplicaInfo(replica_num=self._replica_id(worker_id, replica_id_num), worker_address=worker_address, state=initial_state)
            dep.replicas.append(replica_info)
            self.replica_map[self._replica_id(worker_id, replica_id_num)] = replica_info
            await self.auto_scale_manager.add_replica(worker_id, replica_id_num, num_cpus, num_gpus)
            await self.node_info_cache.update_resources(int(worker_id),num_cpus, num_gpus , add=True)
            return True

    async def move_replica_state(self, deployment_id: int, replica_num: str, worker_id: str, new_state: ReplicaStateName) -> bool:
        async with self._lock:
            rid = self._replica_id(worker_id, replica_num)
            replica = self.replica_map.get(rid)
            if replica:
                replica.state = new_state
                return True
            return False

    async def remove_replica_from_deployment(self, deployment_id: int, replica_id: str, worker_id: str) -> bool:
        async with self._lock:
            rid = self._replica_id(worker_id, replica_id)
            replica = self.replica_map.pop(rid, None)
            dep = self.deployments.get(deployment_id)
            if replica and dep and replica in dep.replicas:
                dep.replicas.remove(replica)
                num_cpus, num_gpus = await self.auto_scale_manager.remove_replica(worker_id, replica_id)
                await self.node_info_cache.update_resources(int(worker_id),num_cpus,num_gpus , add=False)
                return True
            logger.warning(f"Replica {replica_id} not found in deployment {deployment_id} for removal.")
            return False
        
    async def get_replica_info(self, replica_id: str) -> Optional[ReplicaInfo]:
        async with self._lock:
            return self.replica_map.get(replica_id)

    async def get_deployment(self, deployment_id: int) -> Optional[DeploymentHandle]:
        async with self._lock:
            return self.deployments.get(deployment_id)

    async def get_all_deployments(self) -> List[DeploymentHandle]:
        async with self._lock:
            return list(self.deployments.values())

    async def get_current_routing_table(self) -> headnode_service_pb2.RoutingUpdate:
        """Constructs a RoutingUpdate protobuf message from the current deployment state."""
        async with self._lock:
            current_deployments = {
                dep_id: headnode_service_pb2.DeploymentInfoMessage(
                    deployment_id=dep_handle.deployment_id,
                    deployment_name=dep_handle.deployment_name,
                    version=dep_handle.version,
                    status="ACTIVE",
                    replicas=[
                        headnode_service_pb2.ReplicaInfo(
                            replica_id=r.replica_num,
                            address=r.worker_address,
                            state=r.state
                        ) for r in dep_handle.replicas
                    ]
                )
                for dep_id, dep_handle in self.deployments.items()
            }
        return headnode_service_pb2.RoutingUpdate(
            current_deployments=current_deployments,
            timestamp_ns=time.time_ns()
        )
   
    
    #This is asynchronous but has synchronous code inside
    '''
    async def run_autoscaling_loop(self):
        while True:
            #Get all the deployments
            deployments = await self.get_all_deployments()
            for deployment in deployments:
                #Returns how many replicas need to be added or removed
                num_replicas, to_add = self.auto_scale_manager.find_replicas_to_scale(deployment.replicas, deployment.desired_num_requests)
                #No need to scale 
                if num_replicas == 0:
                    continue
                # Call the scheduler to scheduler the replicas
                self.scheduler.schedule_replicas(num_replicas, deployment.deployment_id, to_add)
            await asyncio.sleep(autoscaling_interval)
    '''
                

               