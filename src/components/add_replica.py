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
import requests
from prometheus_client import Histogram, Counter, REGISTRY, start_http_server
import aiohttp
LATENCY_BUCKETS = [0.1, 0.5, 1, 5, 10, 30, 60, 120, 180]

REQUEST_LATENCY = Histogram(
            'replica_request_latency_seconds',
            'Replica request latency in seconds',
            ['deployment_name'],
            buckets=LATENCY_BUCKETS,
            registry=REGISTRY  # Use the same registry as vLLM
        )

REQUEST_COUNT = Counter(
            'replica_requests_total',
            'Total replica requests handled',
            ['deployment_name', 'status'],
            registry=REGISTRY  # Use the same registry as vLLM
        )

FIRST_TOKEN_LATENCY = Histogram(
            'replica_first_token_latency_seconds',
            'Replica first token latency in seconds',
            ['deployment_name'],
            registry=REGISTRY  # Use the same registry as vLLM
        )

INTER_TOKEN_LATENCY = Histogram(
            'replica_inter_token_latency_seconds',
            'Replica inter token latency in seconds',
            ['deployment_name'],
            registry=REGISTRY  # Use the same registry as vLLM
        )

class ReplicaManager():
    def __init__(self,deployment_name, deployment_id,metrics_port, loop):
       
        self.deployment_name = deployment_name
        self.deployment_id = deployment_id
        self.metrics_port = metrics_port
        self.loop = loop
        self.init_model()
        start_http_server(self.metrics_port)
        
        
        
        

    def init_model(self):
        #Use the deployment name to load the model from 
        print(f"[ReplicaManager-{self.deployment_id}] Initializing model")
        #Load the required model from the model config
        self.model_id = model_config.MODEL_CONFIGS[self.deployment_name].model_id

        # Configure vLLM Engine, Todo: Check the configuration of vllm and what works here
        try:
            # Determine device configuration based on num_gpus
    
            engine_args = AsyncEngineArgs(
                model=self.model_id,
                max_num_batched_tokens=262144,  
                max_num_seqs=1024,             
                max_model_len=2048,          
                dtype="float16",             
                trust_remote_code=True,
                device="cuda",               
                gpu_memory_utilization=0.90, 
                  
            )
            # This is a long, blocking call
            self.engine = AsyncLLMEngine.from_engine_args(engine_args)
            print(f"[ReplicaManager-{self.deployment_id}] VLLM Engine initialized.") 
        except Exception as e:
            print(f"[ReplicaManager- {self.deployment_id}] Error loading model: {e}")
            return
    
    def start_polling_metrics(self):
        """Call this from C++ after event loop is running."""
        self.loop.call_soon_threadsafe(
            self.loop.create_task,
            self.poll_metrics_periodically()
        )
    async def generate_stream(self, prompt: str, queue_callback):
        """
        Asynchronously generates tokens and puts them into a queue
        provided by the C++ caller.
        """
        print(f"[ReplicaManager-{self.deployment_id}] generate_stream called with prompt: {prompt[:100]}...")
        print(f"[ReplicaManager-{self.deployment_id}] queue_callback type: {type(queue_callback)}")
        
        sampling_params = SamplingParams(max_tokens=500, temperature=0.7)
        request_id = random_uuid()
        print(f"[ReplicaManager-{self.deployment_id}] Generating stream for request_id: {request_id}")
        results_generator = self.engine.generate(prompt, sampling_params, request_id)
        
        sent_position = 0
        start_time = time.time()
        first_token_received = False
        last_token_received = False
        last_token_time = time.time()
        try:
            async for request_output in results_generator:
                current_text = request_output.outputs[0].text
                new_text = current_text[sent_position:]
                print(f"[ReplicaManager-{self.deployment_id}] Generated text: {new_text}")
                if new_text:
                    # Put the generated text into the C++ queue
                    #print(f"[ReplicaManager-{self.deployment_id}] Calling queue_callback.put with: {new_text[:50]}...")
                    if not first_token_received:
                        ttft = time.time() - start_time
                        first_token_received = True
                        FIRST_TOKEN_LATENCY.labels(deployment_name=self.deployment_name).observe(ttft)
                       
                    queue_callback.put(new_text)
                    sent_position = len(current_text)
                    if last_token_received:
                        INTER_TOKEN_LATENCY.labels(deployment_name=self.deployment_name).observe(time.time() - last_token_time)
                    last_token_received = True
                    last_token_time = time.time()

            # Record latency after the last token is generated
            REQUEST_LATENCY.labels(deployment_name=self.deployment_name).observe(time.time() - start_time)
            REQUEST_COUNT.labels(deployment_name=self.deployment_name, status="success").inc()
            
        except Exception as e:
            # Signal an error
            print(f"[ReplicaManager-{self.deployment_id}] Exception in generate_stream: {e}")
            queue_callback.put(f"[PYTHON ERROR] {str(e)}")
            REQUEST_COUNT.labels(deployment_name=self.deployment_name, status="error").inc()
        finally:
            # Signal the end of the stream with a special sentinel value (None)
            print(f"[ReplicaManager-{self.deployment_id}] Sending None to close stream")
            queue_callback.put(None)

    
           
   
    


