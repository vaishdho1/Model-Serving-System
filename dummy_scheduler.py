import headnode_service_pb2
import headnode_service_pb2_grpc
import grpc
import asyncio
from headstore_client import HeadStoreClient
class HeadNodeManager(headnode_service_pb2_grpc.HeadNodeServiceServicer):
    def __init__(self, node_id, node_address, node_port, head_address, head_port):
        self.worker_id = node_id
        # We basically create a client to the head store on the head node
        self.hsclient = HeadStoreClient(head_address, head_port)
        self.node_address = node_address
        self.node_port = node_port 
        self.head_address = head_address
        self.head_port = head_port
        # register the node with the head node
        #self._register_node()
        # Send regular health updates as a separate thread
    
    async def CreateReplica(self, request, context):
        print(f"[HeadNodeManager-{self.worker_id}] Creating replica...")
        return headnode_service_pb2.ReplicaCreationReply(worker_id=1,replica_id=1,created=True)
    
    
async def main():
    server = grpc.aio.server()
    headnode_service_pb2_grpc.add_HeadNodeServiceServicer_to_server(HeadNodeManager(node_id=1, node_address='localhost', node_port=50054, head_address='localhost', head_port=50051), server)
    server.add_insecure_port('[::]:50054')
    print(f"Server listening on port 50054")
    await server.start()
    await server.wait_for_termination()

asyncio.run(main())