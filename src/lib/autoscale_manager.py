from dataclasses import dataclass
from collections import defaultdict
from httpx import head
from src.generated import headnode_service_pb2, headnode_service_pb2_grpc, worker_service_pb2_grpc
from typing import List
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("AutoScaleManager")
import asyncio
@dataclass
class Replica:
    avg_requests: float
    sent_time_stamp: int
    num_cpus: int
    num_gpus: int
   


class AutoScaleManager:
    def __init__(self): 
       self.replica_map = {}
       self.replica_lock = asyncio.Lock()
      
    
    @staticmethod
    def _replica_id(worker_id: str, replica_num: str) -> str:
        return f"{worker_id}#{replica_num}"
    
    #The main deployment manager adds or removes the replicas when they are created or destroyed
    async def load_metrics(self, request: headnode_service_pb2.MetricsRequest):
        """Update metrics for a replica, if it exists."""
        actual_id = self._replica_id(request.worker_id, request.replica_id)
        async with self.replica_lock:
            replica = self.replica_map.get(actual_id)
            if not replica:
                logger.warning(f"[AutoScaleManager] Replica {actual_id} not found")
                return
            replica.avg_requests = request.avg_requests
            replica.sent_time_stamp = request.sent_time_stamp
            logger.info(f"[AutoScaleManager] Updated metrics for replica {actual_id}")
            
    #When we remove replicas, we return the cpus and gpus to update the node info cache
    async def remove_replica(self, worker_id, replica_id):
        actual_id = self._replica_id(worker_id, replica_id)
        async with self.replica_lock:
            num_cpus = self.replica_map[actual_id].num_cpus
            num_gpus = self.replica_map[actual_id].num_gpus
            del self.replica_map[actual_id]
            logger.info(f"[AutoScaleManager] Removed replica {actual_id}")
            return  num_cpus, num_gpus
    
    async def add_replica(self, worker_id, replica_id, num_cpus, num_gpus):
        actual_id = self._replica_id(worker_id, replica_id)
        async with self.replica_lock:
            self.replica_map[actual_id] = Replica(0, 0, num_cpus, num_gpus)
            logger.info(f"[AutoScaleManager] Added replica {actual_id }")
            return  
    
   