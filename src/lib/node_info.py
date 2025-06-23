from src.generated import worker_service_pb2_grpc, headnode_service_pb2
from collections import defaultdict
import asyncio
import grpc
from dataclasses import dataclass



@dataclass
class Node:
    node_id: int
    node_address: str
    channel: grpc.aio.Channel
    worker_stub: worker_service_pb2_grpc.HeadNodeServiceStub
    resource: headnode_service_pb2.Resource
    used_resources: defaultdict

class NodeInfo:
    def __init__(self):
        self.node_map = {}
        self.node_lock = asyncio.Lock()
    
    async def add_node(self, request: headnode_service_pb2.RegisterRequest):
        channel = grpc.aio.insecure_channel(f"{request.node_address}:{request.port}")
        worker_stub = worker_service_pb2_grpc.HeadNodeServiceStub(channel)
        used_resources = defaultdict(int)
        used_resources["num_cpus"] = 0
        used_resources["num_gpus"] = 0  
        async with self.node_lock:
            self.node_map[request.node_id] = Node(
                request.node_id, f"{request.node_address}:{request.port}", channel, worker_stub, request.resource, used_resources
            )
            #print(f"[NodeInfo] Added node {request.node_id} with {request.resource.num_cpus} CPUs, {request.resource.num_gpus} GPUs. Used: {used_resources['num_cpus']} CPUs, {used_resources['num_gpus']} GPUs")
            return 
        
    async def update_resources(self, node_id, num_cpus, num_gpus, add):
        async with self.node_lock:
            if add:
                self.node_map[node_id].used_resources["num_cpus"] += num_cpus
                self.node_map[node_id].used_resources["num_gpus"] += num_gpus
            else:
                self.node_map[node_id].used_resources["num_cpus"] -= num_cpus
                self.node_map[node_id].used_resources["num_gpus"] -= num_gpus
            #print(f"[NodeInfo] Updated resources for node {node_id}. Used: {self.node_map[node_id].used_resources['num_cpus']} CPUs, {self.node_map[node_id].used_resources['num_gpus']} GPUs")
            return
        
    async def remove_node(self, node_id):
        async with self.node_lock:
            node = self.node_map.pop(node_id, None)
            if node and hasattr(node, 'channel'):
                await node.channel.close()
    
    async def get_node(self, node_id):
        async with self.node_lock:
            return self.node_map[node_id]
        
    async def get_all_nodes(self):
        async with self.node_lock:
            return list(self.node_map.values())