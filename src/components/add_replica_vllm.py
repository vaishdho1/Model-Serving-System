# Start a replica server given the port and send ready reques
from concurrent import futures
from gc import disable
import grpc
from src.generated import worker_service_pb2, worker_service_pb2_grpc, replica_service_pb2_grpc, replica_service_pb2, common_pb2
import grpc
import time
import os
import argparse
from src.lib import model_config
import signal
import asyncio
import torch
from vllm import AsyncLLMEngine, SamplingParams
from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.utils import random_uuid
from prometheus_client import start_http_server, Histogram, Counter, REGISTRY
import requests
from vllm.engine.metrics import Metrics
'''
The server is synchronous. It is stateless just does inference depending on the input that it gets.
Todo: Add VLLM support for efficient inference
'''
#This stores the latency and requests count for the vllm requests.
REQUEST_LATENCY = Histogram(
            'replica_request_latency_seconds',
            'Replica request latency in seconds',
            ['deployment_name', 'replica_id'],
            registry=REGISTRY  # Use the same registry as vLLM
        )

REQUEST_COUNT = Counter(
            'replica_requests_total',
            'Total replica requests handled',
            ['deployment_name', 'replica_id', 'status'],
            registry=REGISTRY  # Use the same registry as vLLM
        )

FIRST_TOKEN_LATENCY = Histogram(
            'replica_first_token_latency_seconds',
            'Replica first token latency in seconds',
            ['deployment_name', 'replica_id'],
            registry=REGISTRY  # Use the same registry as vLLM
        )
       
class ReplicaManager(replica_service_pb2_grpc.WorkerServiceServicer):
    def __init__(self, parent_port, replica_id, port, deployment_name, deployment_id, num_cpus=1, num_gpus=0):
        self.parent_port = parent_port
        self.replica_id = replica_id
        self.port = port
        self.deployment_name = deployment_name
        self.deployment_id = deployment_id
        self.replica_state = "idle"
        self.num_cpus = num_cpus
        self.num_gpus = num_gpus
        self.active_requests = 0
        self.request_lock = asyncio.Lock()
        self.stub  = worker_service_pb2_grpc.ReplicaServiceStub(
            grpc.aio.insecure_channel(f"0.0.0.0:{parent_port}")
        )
        self.pid = os.getpid()
        
        
        self.health_update_interval = 5 
       

        print(f"[ReplicaManager-{self.replica_id}] Initializing with {num_cpus} CPUs, {num_gpus} GPUs")
         # Start Prometheus metrics server
        start_http_server(9000) 
        self.init_model()
        #This polls vllm metrics to send to the head_controller for autoscaling decisions
        asyncio.create_task(self.poll_metrics_periodically())
        
        # Note: register_replica and health updates will be started from main() async context

    def init_model(self):
         #Use the deployment name to load the model from 
         print(f"[ReplicaManager-{self.replica_id}] Initializing model")
         #Load the required model from the model config
         self.model_id = model_config.MODEL_CONFIGS[self.deployment_name].model_id

         # Configure vLLM Engine, Todo: Check the configuration of vllm and what works here
         try:
            # Determine device configuration based on num_gpus
    
            engine_args = AsyncEngineArgs(
                model=self.model_id,
                max_num_batched_tokens=65536,  
                max_num_seqs=512,             
                max_model_len=2048,          
                dtype="float16",             
                trust_remote_code=True,
                device="cuda",               
                gpu_memory_utilization=0.85, 
                  
            )
            self.engine = AsyncLLMEngine.from_engine_args(engine_args)
            print(f"[ReplicaManager-{self.replica_id}] vLLM Engine initialized")
           
         except Exception as e:
            print(f"[ReplicaManager- {self.replica_id}] Error loading model: {e}")
            return
   


    def _get_best_device(self):
        """Auto-detect the best available device for inference"""
        # Only use GPU if num_gpus > 0

        if torch.cuda.is_available():
                return f"cuda:{torch.cuda.current_device()}" 
        # Default to CPU if no GPU requested or available
        return "cpu"
    
    async def StreamGenerate(self, request, context):
        start_time = time.time()
        
        raw_prompt = request.prompt
        print(f"[ReplicaManager-{self.replica_id}] Raw prompt: '{raw_prompt}'")
        
        # Format prompt for TinyLlama chat model
        formatted_prompt = f"<|user|>\n{raw_prompt}<|end|>\n<|assistant|>\n"
        print(f"[ReplicaManager-{self.replica_id}] Formatted prompt: '{formatted_prompt}'")
        
        request_id = random_uuid()
        sampling_params = SamplingParams(
            max_tokens=500,
            temperature=0.7,
            top_p=0.95,
            stop=["<|end|>", "</s>"],
            include_stop_str_in_output=False
            )
        
        # Optimized streaming with position tracking
        sent_position = 0
        start_time = time.time()
        first_token_received = False
        try:
            # Add request and get async generator for real streaming
            results_generator = self.engine.generate(formatted_prompt, sampling_params, request_id)
            
            async for request_output in results_generator:
                
                # Stream only the new tokens, not the entire accumulated text
                for output in request_output.outputs:
                    current_text = output.text
                    current_length = len(current_text)
                    
                    # Only process new content
                    if current_length > sent_position:
                        if not first_token_received:
                            ttft = time.time() - start_time
                            first_token_received = True
                            FIRST_TOKEN_LATENCY.labels(deployment_name=self.deployment_name, replica_id=str(self.replica_id)).observe(ttft)
                           
                        # Extract only the new portion
                        new_text = current_text[sent_position:]
                        if new_text:
                            #print(f"[ReplicaManager-{self.replica_id}] Sending token: '{new_text}'")
                            yield replica_service_pb2.TokenChunk(text=new_text, is_error=False)
                            sent_position = current_length
                
                # If finished, break out of the loop
                if request_output.finished:
                    break
            
                REQUEST_COUNT.labels(
                    deployment_name=self.deployment_name,
                    replica_id=str(self.replica_id),
                    status="success"
                ).inc()
        except Exception as e:
            print(f"[ReplicaManager-{self.replica_id}] vLLM Error: {str(e)}")
            yield replica_service_pb2.TokenChunk(text=f"[vLLM Error] {str(e)}", is_error=True)
            REQUEST_COUNT.labels(
                    deployment_name=self.deployment_name,
                    replica_id=str(self.replica_id),
                    status="error"
                ).inc()
            
        finally:
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(
                    deployment_name=self.deployment_name,
                    replica_id=str(self.replica_id)
                ).observe(duration)

    
    async def poll_metrics_periodically(self):
    
        url = f"http://localhost:{9000}/metrics"
        while True:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    print("--- METRICS SNAPSHOT ---")
                    for line in response.text.splitlines():
                        # Look for both vLLM and our custom replica metrics
                        if any(keyword in line for keyword in ["vllm", "replica_request", "replica_first_token"]) and not line.startswith("#"):
                            print(line)
            except Exception as e:
                print(f"Could not fetch metrics: {e}")
            await asyncio.sleep(2)
           
   
    async def send_with_retries_async(self, coro_func, *args, num_attempts=3, delay_seconds=2, **kwargs):
        #This should try registering and if not successful after num_attempts, it should kill itself
        for attempt in range(1, num_attempts + 1):
            try:
                return await coro_func(*args, **kwargs)
            except grpc.RpcError as e:
                print(f"gRPC error on attempt {attempt}/{num_attempts} sending registration: code={e.code()}, details='{e.details()}'")
                if attempt < num_attempts:
                    print(f"Retrying registration in {delay_seconds} seconds...")
                    await asyncio.sleep(delay_seconds)
        
        print("Failed to register replica after 3 attempts. Terminating process.")
        os.kill(self.pid, signal.SIGTERM)
        return None

    async def register_replica(self):
        print(f"[ReplicaManager-{self.replica_id}] Registering replica")
        
        # Try to register with async retries
        response = await self.send_with_retries_async(
            self.stub.RegisterReplica,
            worker_service_pb2.replicaStatus(
                replica_id = self.replica_id,
                pid = self.pid,
                port = self.port,
                state = self.replica_state,
                deployment_id = self.deployment_id)
        )
        
        if response:  # Only print success if we got a response
            print(f"[ReplicaManager-{self.replica_id}] Replica registered, starting health updates")
            asyncio.create_task(self.send_health_updates())


    def load_and_run_model(self,model,input):
        print("Loading model")
        #Todo need to run the model inference here
        time.sleep(10)
        return f"done {model}"
 
    
    # Health ping from the worker node
    def Ping(self, request, context):
        print(f"[ReplicaManager-{self.replica_id}] Received ping from head node : {time.time()}")
        return common_pb2.Ack(acknowledged=True)
    '''
    def PushTask(self, request, context):
        print(f"[ReplicaManager-{self.replica_id}] Received task from worker")
        model = request.model
        input = request.input
        res = self.load_and_run_model(model, input)
        print(f"[ReplicaManager-{self.replica_id}] Sending output to worker {res}")
        return worker_service_pb2.TaskReply(result=res)
    '''
    
    async def send_health_updates(self):
        while True:
            success_this_cycle = False # Reset for each health update cycle
            for attempt in range(1, 4): 
                try:
                    print(f"Attempting to send health update (Attempt {attempt}/3)...")
                    response = await self.stub.sendHealthupdate(worker_service_pb2.HealthStatus(replica_id=self.replica_id, status="healthy"))

                    if response.ack == 0:
                        print("Health update response indicates worker considers replica dead. Terminating process.")
                        os.kill(self.pid, signal.SIGTERM)
                        return # Exit task as process is terminating
                    
                    print("Health update sent successfully.")
                    success_this_cycle = True
                    break # Exit retry loop on success
                
                except grpc.RpcError as e:
                    print(f"gRPC error on attempt {attempt}/3 sending health update: code={e.code()}, details='{e.details()}'")
                except Exception as e:
                    print(f"Error on attempt {attempt}/3 sending health update: {e}")
                
                if attempt < 3: # If not the last attempt
                    print("Retrying health update in 2 seconds...")
                    await asyncio.sleep(2) # Use async sleep

            if not success_this_cycle:
                print("Failed to send health update after 3 attempts. Terminating process.")
                os.kill(self.pid, signal.SIGTERM)
                return # Exit task as process is terminating
            
            # Wait for the configured interval before the next health update cycle
            await asyncio.sleep(self.health_update_interval)


        


async def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--replica_id", type=str, required=True)
    parser.add_argument("--parent_port", type=str, required=True)
    parser.add_argument("--port", type=str, required=True)
    parser.add_argument("--deployment_name", type=str, required=True)
    parser.add_argument("--deployment_id", type=str, required=True)
    parser.add_argument("--num_cpus", type=str, required=True)
    parser.add_argument("--num_gpus", type=str, required=True)

    args = parser.parse_args()
    
    # Create replica manager and initialize the model
    replica_manager = ReplicaManager(args.parent_port, int(args.replica_id), args.port, args.deployment_name, int(args.deployment_id), int(args.num_cpus), int(args.num_gpus))
    
    # Start the server
    server = grpc.aio.server()
    replica_service_pb2_grpc.add_WorkerServiceServicer_to_server(replica_manager, server)
    server.add_insecure_port(f"0.0.0.0:{args.port}")
    await server.start()

    print(f"Replica {args.replica_id} listening on port {args.port}")
    
    # Wait for server to be fully ready before registering
    await asyncio.sleep(2)  # Non-blocking async sleep
    
    # Register replica asynchronously
    await replica_manager.register_replica()
    
    print(f"[Replica-{args.replica_id}] Registration complete, server ready for requests")
    await server.wait_for_termination()
    
    
    
    # Start health updates asynchronously after server is running
   


if __name__ == "__main__":
    asyncio.run(main())


