import headnode_service_pb2
import headnode_service_pb2_grpc
import grpc
import asyncio
import time
import random
count = 1
class HeadNodeServicer(headnode_service_pb2_grpc.HeadNodeServiceServicer):
    """Implements RPCs that the Scheduler calls on this Head Node server."""
    async def RegisterNode(self, request: headnode_service_pb2.RegisterRequest, context):
        print(f"[SimpleHeadServer] Scheduler registered: Node ID {request.node_id} at {request.node_address}:{request.port}, State: {request.state}")
        return headnode_service_pb2.RegisterReply(ack=True)

    async def SendHealthStatus(self, request: headnode_service_pb2.HealthStatusUpdate, context):
        global count
        print(f"[SimpleHeadServer] Received health from Scheduler {count} times with Node ID {request.worker_id}: State {request.state}: {time.time()}")
        print("The length of the replica states is: ",len(request.replica_states))
        for rs in request.replica_states:
            print(f"  -> Replica ID: {rs.replica_id}, Queue: {rs.queue_size}, Status: {rs.status}")
        # Always acknowledge positively in this simple version
        count += 1
        #should_nack  = count==6
        #if should_nack:
        #    print(f"[SimpleHeadServer] Intentionally NACKing health update for Node ID {request.worker_id}.")
        #    return headnode_service_pb2.HealthStatusReply(ack=False, isAlive="true")
        return headnode_service_pb2.HealthStatusReply(ack=True, isAlive="true")

async def client_side_calls(port):
    await asyncio.sleep(5) # Initial delay
    channel = None # Initialize channel to None for finally block
    output_replica1, output_replica2 = None, None # To store replica creation results

    try:
        channel = grpc.aio.insecure_channel(f'localhost:{port}')
        stub = headnode_service_pb2_grpc.HeadNodeServiceStub(channel)

        print("[ClientCalls] Stage 1: Sending 2 CreateReplica requests in parallel...")
        create_replica_coro1 = stub.CreateReplica(headnode_service_pb2.ReplicaCreationRequest(base_node_address='localhost', num_resources=1, resource_name='CPU'))
        create_replica_coro2 = stub.CreateReplica(headnode_service_pb2.ReplicaCreationRequest(base_node_address='localhost', num_resources=1, resource_name='CPU'))
        create_replica_coro3 = stub.CreateReplica(headnode_service_pb2.ReplicaCreationRequest(base_node_address='localhost', num_resources=1, resource_name='CPU'))
        create_replica_coro4 = stub.CreateReplica(headnode_service_pb2.ReplicaCreationRequest(base_node_address='localhost', num_resources=1, resource_name='CPU'))


        results_create = await asyncio.gather(create_replica_coro1, create_replica_coro2, create_replica_coro3, create_replica_coro4, return_exceptions=True)
        
        # Check results of CreateReplica calls
        if isinstance(results_create[0], Exception):
            print(f"[ClientCalls] Error creating replica 1: {results_create[0]}")
            return # Stop if first replica creation failed
        output_replica1 = results_create[0]

        if isinstance(results_create[1], Exception):
            print(f"[ClientCalls] Error creating replica 2: {results_create[1]}")
            return # Stop if second replica creation failed
        output_replica2 = results_create[1]

        if isinstance(results_create[2], Exception):
            print(f"[ClientCalls] Error creating replica 3: {results_create[2]}")
            return # Stop if third replica creation failed
        output_replica3 = results_create[2]

        if isinstance(results_create[3], Exception):
            print(f"[ClientCalls] Error creating replica 4: {results_create[3]}")
            return # Stop if fourth replica creation failed
        output_replica4 = results_create[3]
        

        print("[ClientCalls] CreateReplica results received.")
        print(f"Replica 1 created with id: {output_replica1.replica_id}")
        print(f"Replica 2 created with id: {output_replica2.replica_id}")
        print(f"Replica 3 created with id: {output_replica3.replica_id}")
        print(f"Replica 4 created with id: {output_replica4.replica_id}")
        '''
        # Stage 2: Send 3 requests to each replica in parallel
        print("[ClientCalls] Stage 2: Sending 3 SendRequest calls to each of the 2 replicas in parallel (6 total SendRequest calls)...")
        
        send_request_coroutines = []

        # Prepare 3 requests for replica 1
        for i in range(3):
            msg_r1 = headnode_service_pb2.Message(model=f"model_r1_{i+1}", input=f"hello_replica1_req{i+1}")
            req_r1 = headnode_service_pb2.ReplicaRequest(worker_id=1, replica_id=output_replica1.replica_id, message=msg_r1)
            print(f"[ClientCalls] Preparing request for Replica {output_replica1.replica_id}: {req_r1.message.model}")
            send_request_coroutines.append(stub.SendRequest(req_r1))

        # Prepare 3 requests for replica 2
        for i in range(3):
            msg_r2 = headnode_service_pb2.Message(model=f"model_r2_{i+1}", input=f"hello_replica2_req{i+1}")
            req_r2 = headnode_service_pb2.ReplicaRequest(worker_id=1, replica_id=output_replica2.replica_id, message=msg_r2)
            print(f"[ClientCalls] Preparing request for Replica {output_replica2.replica_id}: {req_r2.message.model}")
            send_request_coroutines.append(stub.SendRequest(req_r2))
        
        # Run all 6 SendRequest calls concurrently
        results_send = await asyncio.gather(*send_request_coroutines, return_exceptions=True)
        
        print("[ClientCalls] All SendRequest results/errors received.")
        
        # Determine which replica each response belongs to for logging
        for i, res_or_exc in enumerate(results_send):
            current_replica_id_for_log = None
            original_model_name_for_log = "unknown_model"
            if i < 3: # First 3 requests were for replica 1
                current_replica_id_for_log = output_replica1.replica_id
                original_model_name_for_log = f"model_r1_{i+1}"
            else: # Next 3 requests were for replica 2
                current_replica_id_for_log = output_replica2.replica_id
                original_model_name_for_log = f"model_r2_{i-3+1}"

            if isinstance(res_or_exc, Exception):
                print(f"  Error sending request {original_model_name_for_log} to replica {current_replica_id_for_log}: {res_or_exc}")
            else:
                # Assuming the response object has an 'output' field based on your previous ReplicaReply definition
                response_output = getattr(res_or_exc, 'output', '[no output field]')
                print(f"  Response for {original_model_name_for_log} from replica {current_replica_id_for_log}: {response_output}")
        '''
    except Exception as e:
        print(f"[ClientCalls] An unexpected error occurred: {e}")
    finally:
        if channel: # Ensure channel was created before trying to close
            await channel.close()
            print("[ClientCalls] Channel closed.")

async def run_server(port):
    server = grpc.aio.server()
    headnode_service_pb2_grpc.add_HeadNodeServiceServicer_to_server(HeadNodeServicer(), server)
    listen_addr = f'[::]:{50054}'
    server.add_insecure_port(listen_addr)
    print(f"[SimpleHeadServer] Starting server, listening on {listen_addr}")
    task1 = asyncio.create_task(client_side_calls(port))
    #task1.add_done_callback(lambda _: print("[SimpleHeadServer] Client side calls done"))
    await server.start()
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        print("[SimpleHeadServer] Server task cancelled, stopping server.")
        await server.stop(0.5) # Short grace period
        print("[SimpleHeadServer] Server stopped.")

async def main():
    await run_server(50051)
    
if __name__ == '__main__':
    asyncio.run(main())
