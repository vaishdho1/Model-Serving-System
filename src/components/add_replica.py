# Start a replica server given the port and send ready reques
from concurrent import futures
import grpc
from src.generated import worker_service_pb2, worker_service_pb2_grpc, replica_service_pb2_grpc, replica_service_pb2
import grpc
from dataclasses import dataclass
from concurrent import futures
import subprocess
import time
import os
import threading
import queue
import argparse
from src.lib import configurations, HeadStoreClient, FutureManager, Replica, model_config
import signal
import asyncio
import torch
import threading
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
import accelerate


'''
The server is synchronous. It is stateless just does inference depending on the input that it gets.
Todo: Add VLLM support for efficient inference
'''

class ReplicaManager(replica_service_pb2_grpc.WorkerServiceServicer):
    def __init__(self, parent_port, replica_id, port, deployment_name, deployment_id):
        self.parent_port = parent_port
        self.replica_id = replica_id
        self.port = port
        self.deployment_name = deployment_name
        self.deployment_id = deployment_id
        self.replica_state = "idle"
        self.stub  = worker_service_pb2_grpc.ReplicaServiceStub(
            grpc.insecure_channel(f"localhost:{parent_port}")
        )
        self.pid = os.getpid()
        
        self.health_update_interval = 5 
        self.init_model()
        #Commented for now
        self.register_replica()
         # Start health update thread as a daemon thread
         #Commented out for now
        self.health_thread = threading.Thread(target=self.send_health_updates)
        self.health_thread.daemon = True
        self.health_thread.start()

    def init_model(self):
         #Use the deployment name to load the model from 
         print(f"[ReplicaManager-{self.replica_id}] Initializing model")
         #Load the required model from the model config
         self.model_id = model_config.MODEL_CONFIGS[self.deployment_name].model_id
         self.device = "cpu"
         self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)

         if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

         self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=torch.float32,
            device_map={"": self.device},
            trust_remote_code=True
        )
         print(f"[ReplicaManager- {self.replica_id}] Model loaded successfully!")

        
    
    def StreamGenerate(self, request, context):
        print(f"[ReplicaManager-{self.replica_id}] Streaming generate")
        prompt = request.prompt
        formatted = f"### Instruction:\n{prompt}\n\n### Response:\n"
        inputs = self.tokenizer(formatted, return_tensors="pt")

        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)

        generation_thread = threading.Thread(
            target=self.model.generate,
            kwargs={
                "input_ids": inputs["input_ids"],
                "attention_mask": inputs["attention_mask"],
                "max_new_tokens": 100,
                "temperature": 0.7,
                "do_sample": True,
                "streamer": streamer
            }
        )
        generation_thread.start()

        for token in streamer:
            yield replica_service_pb2.TokenChunk(text=token)
       
    def send_with_retries(self, coro_func, *args, num_attempts=3, delay_seconds=2, **kwargs):
        #This should try registering and if not succesful after num_attemps, it should kill itself
        for attempt in range(1, num_attempts + 1):
            try:
                return coro_func(*args, **kwargs)
            except grpc.RpcError as e:
                print(f"gRPC error on attempt {attempt}/3 sending health update: code={e.code()}, details='{e.details()}'")
        
        print("Failed to send health update after 3 attempts. Terminating process.")
        os.kill(self.pid, signal.SIGTERM)
        return

    def register_replica(self):
        print(f"[ReplicaManager-{self.replica_id}] Registering replica")
        
        # Try to register, but only retry on failure
        response = self.send_with_retries(
            self.stub.RegisterReplica,
            worker_service_pb2.replicaStatus(
                replica_id = self.replica_id,
                pid = self.pid,
                port = self.port,
                state = self.replica_state,
                deployment_id = self.deployment_id)
        )
        
        if response:  # Only print success if we got a response
            print(f"[ReplicaManager-{self.replica_id}] Replica registered")
        #self.stub.RegisterReplica(worker_service_pb2.replicaStatus(replica_id = self.replica_id, pid = self.pid, port = self.port, state = self.replica_state))
        #self.stub.RegisterReplica(RegisterReplicaRequest(replica_id = self.replica_id, pid = self.pid, port = self.port,replica_state = self.replica_state))

    def load_and_run_model(self,model,input):
        print("Loading model")
        #Todo need to run the model inference here
        time.sleep(10)
        return f"done {model}"
 
    
    # Health ping from the worker node
    def Ping(self, request, context):
        print(f"[ReplicaManager-{self.replica_id}] Received ping from head node : {time.time()}")
        return worker_service_pb2.Ack(acknowledged=True)
    '''
    def PushTask(self, request, context):
        print(f"[ReplicaManager-{self.replica_id}] Received task from worker")
        model = request.model
        input = request.input
        res = self.load_and_run_model(model, input)
        print(f"[ReplicaManager-{self.replica_id}] Sending output to worker {res}")
        return worker_service_pb2.TaskReply(result=res)
    '''
    
    def send_health_updates(self):
        while True:
            success_this_cycle = False # Reset for each health update cycle
            for attempt in range(1, 4): 
                try:
                    print(f"Attempting to send health update (Attempt {attempt}/3)...")
                    response = self.stub.sendHealthupdate(worker_service_pb2.HealthStatus(replica_id=self.replica_id, status="healthy"))

                    if response.ack == 0:
                        print("Health update response indicates worker considers replica dead. Terminating process.")
                        os.kill(self.pid, signal.SIGTERM)
                        return # Exit thread as process is terminating
                    
                    print("Health update sent successfully.")
                    success_this_cycle = True
                    break # Exit retry loop on success
                
                except grpc.RpcError as e:
                    print(f"gRPC error on attempt {attempt}/3 sending health update: code={e.code()}, details='{e.details()}'")
                except Exception as e:
                    print(f"Error on attempt {attempt}/3 sending health update: {e}")
                
                if attempt < 3: # If not the last attempt
                    print("Retrying health update in 2 seconds...")
                    time.sleep(2) # Wait before retrying

            if not success_this_cycle:
                print("Failed to send health update after 3 attempts. Terminating process.")
                os.kill(self.pid, signal.SIGTERM)
                return # Exit thread as process is terminating
            
            # Wait for the configured interval before the next health update cycle
            time.sleep(self.health_update_interval)


        


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--replica_id", type=int, required=True)
    parser.add_argument("--parent_port", type=str, required=True)
    parser.add_argument("--port", type=str, required=True)
    parser.add_argument("--deployment_name", type=str, required=True)
    parser.add_argument("--deployment_id", type=int, required=True)
    parser.add_argument("--num_cpus", type=int, required=True)
    parser.add_argument("--num_gpus", type=int, required=True)

    args = parser.parse_args()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    replica_service_pb2_grpc.add_WorkerServiceServicer_to_server(
        ReplicaManager(args.parent_port, args.replica_id, args.port, args.deployment_name, args.deployment_id), server
    )
    server.add_insecure_port(f"[::]:{args.port}")
    server.start()
    print(f"Replica {args.replica_id} listening on port {args.port}")
    server.wait_for_termination()

if __name__ == "__main__":
    main()


#