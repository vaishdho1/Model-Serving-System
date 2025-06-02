import asyncio
import subprocess
from src.generated import headnode_service_pb2, headnode_service_pb2_grpc
import google.protobuf.empty_pb2
import grpc
from src.lib.configurations import proxy_ping_max_retries, proxy_ping_retry_delay, proxy_ping_interval


'''
Starts the httpproxy as a separate process.
Sends changing updates to the the proxy
Restarts the proxy if it dies
'''
async def try_send_with_retries(coro_func, *args, num_attempts=3, delay_seconds=2, **kwargs):
    """Helper function to retry an async operation that might raise grpc.RpcError."""
    last_exception = None
    for attempt in range(1, num_attempts + 1):
        try:
            #print(f"[RetryHelper] Attempt {attempt}/{num_attempts} calling {coro_func.__name__}") # Optional: for more verbose logging
            return await coro_func(*args, **kwargs)
        except grpc.RpcError as e:
            print(f"[RetryHelper] Attempt {attempt}/{num_attempts} failed for {getattr(coro_func, '__name__', 'rpc_call')}: {e.code()} - {e.details()}")
            last_exception = e
            if attempt < num_attempts:
                print(f"[RetryHelper] Retrying in {delay_seconds} seconds...")
                await asyncio.sleep(delay_seconds)
        # Consider if other exceptions should be caught and retried, or allowed to propagate immediately.

class ProxyManager(headnode_service_pb2_grpc.ProxyManagementServiceServicer):
    def __init__(self, node_port, http_port, grpc_port):
        self.node_port = node_port
        self.http_port = http_port
        self.grpc_port = grpc_port
        self.isAlive = False
        self._proxy_stub = None
        self._proxy_channel = None
         # Start the proxy and its health monitoring tasks
        asyncio.create_task(self._initialize_proxy())

    async def _initialize_proxy(self):
        print("[ProxyManager] Initializing HTTP proxy...")
        started = await self.start_http_proxy()
        if started:
            print("[ProxyManager] HTTP proxy process start initiated. Creating proxy channel for health checks.")
            await self.create_proxy_channel_and_stub()
        else:
            print("[ProxyManager] Failed to initiate HTTP proxy process start.")
        return

   
    async def create_proxy_channel_and_stub(self):
        if self.isAlive:
            return
        if self._proxy_channel is None:
            self.isAlive = True
            proxy_grpc_address = f"localhost:{self.grpc_port}"
            print(f"[ProxyManager] Creating gRPC channel to proxy at {proxy_grpc_address}")
            self._proxy_channel = grpc.aio.insecure_channel(proxy_grpc_address)
            self._proxy_stub = headnode_service_pb2_grpc.ProxyManagementServiceStub(self._proxy_channel)
            # Once connected start the health check loop
            asyncio.create_task(self.find_health_status())
        return

    async def send_routing_update(self, update_message):
       # Returning the update message
       return headnode_service_pb2.RoutingUpdate(update_message)

    async def start_http_proxy(self):
        cmd = [
            "python3", "http_proxy.py", 
            "--parent_port", str(self.node_port), # Port of this scheduler node
            "--http_port", str(self.http_port),   # Port for the new replica's server
            "--grpc_port", str(self.grpc_port)
        ]
        
        try:
            log_file_name = f"http_proxy.log"
            print(f"[ProxyManager] Redirecting output of httpproxy to {log_file_name}")
            with open(log_file_name, "w") as log_file:
                    subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
        except Exception as e:
            print(f"[ProxyManager] Error starting http proxy: {e}")
            return False
        return True
    
   

    async def find_health_status(self):
        print(f"[ProxyManager] Starting health check loop for proxy on gRPC port {self.grpc_port}")
        while True:
            # Ensured that this starts only after the proxy is up
            ping_successful = False
            try:
                print(f"[ProxyManager] Pinging proxy at localhost:{self.grpc_port}")
                ack_reply = await try_send_with_retries(
                    self._proxy_stub.Ping, 
                    google.protobuf.empty_pb2.Empty(), 
                    num_attempts=proxy_ping_max_retries, 
                    delay_seconds=proxy_ping_retry_delay
                )
                #Need to check this
                if ack_reply and ack_reply.success:
                    ping_successful = True
                else:
                    print(f"[ProxyManager] Ping to proxy failed or returned not success. Ack: {ack_reply}")
            except grpc.RpcError as e:
                print(f"[ProxyManager] gRPC error during ping to proxy: {e.code()} - {e.details()}")
                if self._proxy_channel:
                    await self._proxy_channel.close()
                self._proxy_channel = None
                self._proxy_stub = None
            except Exception as e:
                print(f"[ProxyManager] Unexpected error during health check: {e}")
                if self._proxy_channel:
                    await self._proxy_channel.close()
                self._proxy_channel = None
                self._proxy_stub = None

            if not ping_successful:
                print(f"[ProxyManager] HTTP proxy appears to be down or unresponsive. Attempting restart...")
                self.isAlive = False
                restarted = await self._initialize_proxy()
                if restarted:
                    print("[ProxyManager] Proxy restart initiated.")
                    if self._proxy_channel:
                        await self._proxy_channel.close()
                    self._proxy_channel = None
                    self._proxy_stub = None
                    await asyncio.sleep(5)
                else:
                    print("[ProxyManager] Failed to initiate proxy restart.")
            
            await asyncio.sleep(proxy_ping_interval)
        
              
         
         


