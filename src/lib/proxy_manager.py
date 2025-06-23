import subprocess
import asyncio
import grpc
from src.generated import proxy_service_pb2, proxy_service_pb2_grpc
from src.lib.helpers import try_send_with_retries
from src.lib.configurations import proxy_heartbeat_interval
from google.protobuf import empty_pb2

class ProxyManager():
    def __init__(self, node_port, http_port, grpc_port):
        self.node_port = node_port
        self.http_port = http_port
        self.grpc_port = grpc_port
        self.AliveProxy = False
        self.start_http_proxy()
        # Give the proxy some time to start up
        #asyncio.sleep(2)
    

    def start_http_proxy(self):
        cmd = [
            "python3", "-u", "-m", "src.components.headNode.http_proxy",
            "--parent_port", str(self.node_port),
            "--http_port", str(self.http_port),
            "--grpc_port", str(self.grpc_port),
        ]
        print(f"[ProxyManager] Starting http proxy")
        
        try:
            log_file_name = f"proxy.log"
            print(f"[ProxyManager] Redirecting output of proxy to {log_file_name}")
            with open(log_file_name, "w") as log_file:
                self.proxy_process = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
                if self.proxy_process.poll() is None:  # Check if process started successfully
                    self.AliveProxy = True
                    print(f"[ProxyManager] HTTP proxy started successfully")
                else:
                    print(f"[ProxyManager] HTTP proxy failed to start")
                    self.AliveProxy = False
        except Exception as e:
            print(f"[ProxyManager] Failed to start http proxy: {e}")
            self.AliveProxy = False

    async def send_heartbeat(self):
        if not self.AliveProxy:
            print(f"[ProxyManager] Proxy not alive, restarting...")
            self.start_http_proxy()
            await asyncio.sleep(2)  # Give time for proxy to start
            
        self.channel = grpc.aio.insecure_channel(f"localhost:{self.grpc_port}")
        self.stub = proxy_service_pb2_grpc.HealthServiceStub(self.channel)
        
        while True:
            try:
                if not self.AliveProxy:
                    print(f"[ProxyManager] Proxy not alive, restarting...")
                    self.start_http_proxy()
                    await asyncio.sleep(2)  # Give time for proxy to start
                    # Need to re-establish channel and stub if proxy was restarted
                    if self.channel:
                        await self.channel.close()
                    self.channel = grpc.aio.insecure_channel(f"localhost:{self.grpc_port}")
                    self.stub = proxy_service_pb2_grpc.HealthServiceStub(self.channel)
                    continue
                    
                print(f"[ProxyManager] Sending heartbeat")
                
                result = await try_send_with_retries(self.stub.Ping, empty_pb2.Empty())
                #print(f"[ProxyManager] Heartbeat result: {result}")
                
                
                if isinstance(result, Exception):  
                    print(f"[ProxyManager] Failed to send heartbeat: All retries exhausted - {result}")
                    self.AliveProxy = False
                    await self.channel.close()
                    if self.proxy_process and self.proxy_process.poll() is None:
                        self.proxy_process.terminate()
                    await asyncio.sleep(1)  
                    continue  
                
               
                #print(f"[ProxyManager] Heartbeat successful")
                await asyncio.sleep(proxy_heartbeat_interval)
                
            except Exception as e:
                print(f"[ProxyManager] Exception in heartbeat loop: {e}")
                self.AliveProxy = False
                if self.channel:
                    await self.channel.close()
                if self.proxy_process and self.proxy_process.poll() is None:
                    self.proxy_process.terminate()
                await asyncio.sleep(1) 
            