'''
This is the main serve controller that is used for 
autoscaling replicas
starting the http proxy and making sure its running
Sending deployment changes to the proxy.
This is where your health checks come.

'''
from src.generated import headnode_service_pb2, headnode_service_pb2_grpc
import subprocess
from src.lib import ProxyManager

class HeadController(headnode_service_pb2_grpc.HeadNodeServiceServicer):

    def __init__(self):
        #Right after start up it start a http proxy as a separate process with a port assigned to it
        self.http_port = 8000
        self.grpc_port = 50051
        self.node_port = 50054
        self.proxy_manager = ProxyManager(self.node_port, self.http_port, self.grpc_port)
        self.start_http_proxy()
        self.isAliveProxy = True


    def start_http_proxy(self):
        cmd = [
            "python3", "add_replica.py", 
            "--parent_port", str(self.node_port), # Port of this scheduler node
            "--http_port", str(self.http_port),   # Port for the new replica's server
            "--grpc_port", str(self.grpc_port)
        ]
        # Todo: Need to start the http proxy as a separate process
        