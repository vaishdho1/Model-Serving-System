import subprocess
import asyncio
import async
import proxy_service_pb2
import proxy_service_pb2_grpc

class ProxyManager(proxy_service_pb2_grpc.ProxyServiceServicer):
    def __init__(self, node_port, http_port, grpc_port):
        self.node_port = node_port
        self.http_port = http_port
        self.grpc_port = grpc_port
        self.AliveProxy = False
        self.start_http_proxy()
    

    def start_http_proxy(self):

        cmd = [
            "python3", "add_replica.py", 
            "--parent_port", str(self.node_port), # Port of this scheduler node
            "--http_port", str(self.http_port),   # Port for the new replica's server
            "--grpc_port", str(self.grpc_port)
        ]
        print(f"[ProxyManager-] Starting http proxy")
        
        try:
            # Open a log file for the replica
            log_file_name = f"replica_{replica_id}.log"
            print(f"[Scheduler-{self.worker_id}] Redirecting output of replica {replica_id} to {log_file_name}")
            with open(log_file_name, "w") as log_file:
                subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        except Exception as e:
            print(f"[ProxyManager-] Failed to start http proxy: {e}")
            self.AliveProxy = False

    async def SendHealthUpdate(self, request, context):
        #Send a health update to the proxy
        print(f"[ProxyManager-] Sending health update to the proxy")
        #Add more robust control
        return proxy_service_pb2.HealthReply(ack=True)
    
    async def send_heartbeat(self):

        while True:
