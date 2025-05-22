# Start a replica server given the port and send ready reques
from concurrent import futures
import grpc
import worker_service_pb2
import worker_service_pb2_grpc
import headnode_service_pb2
import headnode_service_pb2_grpc
import multiprocessing
import grpc
from dataclasses import dataclass
from concurrent import futures
import subprocess
import time
import os
import worker_service_pb2
import worker_service_pb2_grpc
import threading
import queue
import argparse
import configurations
import signal
import asyncio
from future_manager import FutureManager
from headstore_client import HeadStoreClient
from replica import Replica


'''
The server is synchronous. It is stateless just does inference depending on the input that it gets.
Todo: Add VLLM support for efficient inference
'''

class ReplicaManager(worker_service_pb2_grpc.WorkerServiceServicer):
    def __init__(self, parent_port, replica_id, port):
        self.parent_port = parent_port
        self.replica_id = replica_id
        self.port = port
        self.replica_state = "idle"
        self.stub = self.stub = worker_service_pb2_grpc.WorkerServiceStub(
            grpc.insecure_channel(f"localhost:{parent_port}")
        )
        self.pid = os.getpid()
        self.register_replica()
        self.health_update_interval = 5 
        # Start health update thread as a daemon thread
        
        self.health_thread = threading.Thread(target=self.send_health_updates)
        self.health_thread.daemon = True
        self.health_thread.start()
        
       
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
        self.send_with_retries(
            self.stub.RegisterReplica,
            worker_service_pb2.replicaStatus(
                                            replica_id = self.replica_id,
                                            pid = self.pid,
                                            port = self.port,
                                            state = self.replica_state)
                            )

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

    def PushTask(self, request, context):
        print(f"[ReplicaManager-{self.replica_id}] Received task from worker")
        model = request.model
        input = request.input
        res = self.load_and_run_model(model, input)
        print(f"[ReplicaManager-{self.replica_id}] Sending output to worker {res}")
        return worker_service_pb2.TaskReply(result=res)
    
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
    parser.add_argument("--num_resources", type=int, required=False)
    parser.add_argument("--resource_type", type=str, required=False)
    parser.add_argument("--parent_port", type=str, required=True)
    parser.add_argument("--port", type=str, required=True)
    args = parser.parse_args()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    worker_service_pb2_grpc.add_WorkerServiceServicer_to_server(
        ReplicaManager(args.parent_port, args.replica_id, args.port), server
    )
    server.add_insecure_port(f"[::]:{args.port}")
    server.start()
    print(f"Replica {args.replica_id} listening on port {args.port}")
    server.wait_for_termination()

if __name__ == "__main__":
    main()