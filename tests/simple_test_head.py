import asyncio
import grpc
import argparse
from src.generated import headnode_service_pb2
from src.generated import headnode_service_pb2_grpc
import sys # For sys.exit in case of fatal client errors

# Configuration
DEFAULT_HEAD_LISTEN_PORT = 50052
DEFAULT_SCHEDULER_ADDRESS = "localhost:50051"

class HeadNodeServicer(headnode_service_pb2_grpc.HeadNodeServiceServicer):
    """Implements RPCs that the Scheduler calls on this Head Node server."""
    async def RegisterNode(self, request: headnode_service_pb2.RegisterRequest, context):
        print(f"[SimpleHeadServer] Scheduler registered: Node ID {request.node_id} at {request.node_address}:{request.port}, State: {request.state}")
        return headnode_service_pb2.RegisterReply(ack=True)

    async def SendHealthStatus(self, request: headnode_service_pb2.HealthStatusUpdate, context):
        print(f"[SimpleHeadServer] Received health from Scheduler Node ID {request.worker_id}: State {request.state}")
        for rs in request.replica_states:
            print(f"  -> Replica ID: {rs.replica_id}, Queue: {rs.queue_size}, Status: {rs.status}")
        # Always acknowledge positively in this simple version
        return headnode_service_pb2.HealthStatusReply(ack=True, isAlive="true")

async def run_server(port: int):
    server = grpc.aio.server()
    headnode_service_pb2_grpc.add_HeadNodeServiceServicer_to_server(HeadNodeServicer(), server)
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    print(f"[SimpleHeadServer] Starting server, listening on {listen_addr}")
    await server.start()
    try:
        await server.wait_for_termination()
    except asyncio.CancelledError:
        print("[SimpleHeadServer] Server task cancelled, stopping server.")
        await server.stop(0.5) # Short grace period
        print("[SimpleHeadServer] Server stopped.")


async def perform_client_actions(scheduler_address: str):
    print(f"[SimpleHeadClient] Connecting to scheduler at {scheduler_address}...")
    created_replica_id = None

    try:
        async with grpc.aio.insecure_channel(scheduler_address) as channel:
            stub = headnode_service_pb2_grpc.HeadNodeServiceStub(channel)

            # 1. Send CreateReplica request
            print("[SimpleHeadClient] Sending CreateReplica request to scheduler...")
            create_replica_req = headnode_service_pb2.ReplicaCreationRequest(
                base_node_address="localhost",
                num_resources=1,
                resource_name="CPU"
            )
            try:
                create_reply = await stub.CreateReplica(create_replica_req, timeout=10)
                if create_reply and create_reply.created:
                    created_replica_id = create_reply.replica_id
                    print(f"[SimpleHeadClient] CreateReplica successful. Scheduler created Replica ID: {created_replica_id} on Worker ID: {create_reply.worker_id}")
                else:
                    print(f"[SimpleHeadClient] CreateReplica failed or not created. Reply: {create_reply}")
                    return # Stop if replica creation failed
            except grpc.RpcError as e:
                print(f"[SimpleHeadClient] CreateReplica RPC failed: {e.code()} - {e.details()}")
                return # Stop if RPC failed

            if not created_replica_id:
                print("[SimpleHeadClient] No replica ID obtained, cannot send task request.")
                return

            # Give a moment for the replica to potentially register with the scheduler
            # This is a guess; in a real system, you'd have better synchronization
            await asyncio.sleep(2) 

            # 2. Send SendRequest (actual task) to the scheduler for the created replica
            print(f"[SimpleHeadClient] Sending SendRequest (task) for Replica ID {created_replica_id} to scheduler...")
            task_message = headnode_service_pb2.Message(model="test_model", input="hello world from simple_test_head")
            send_request_req = headnode_service_pb2.ReplicaRequest(
                # worker_id is often set by the scheduler, or might be known.
                # If your scheduler assigns worker_id on ReplicaCreationReply, use create_reply.worker_id
                # For simplicity, let's assume worker_id for task routing isn't strictly needed by scheduler's SendRequest
                # or that it can infer it from replica_id. If scheduler needs it, adjust here.
                worker_id=create_reply.worker_id if 'create_reply' in locals() and hasattr(create_reply, 'worker_id') else 0, 
                replica_id=created_replica_id,
                message=task_message
            )
            try:
                task_reply = await stub.SendRequest(send_request_req, timeout=10)
                print(f"[SimpleHeadClient] SendRequest successful. Reply from Replica ID {task_reply.replica_id} (via worker {task_reply.worker_id}): '{task_reply.output}'")
            except grpc.RpcError as e:
                print(f"[SimpleHeadClient] SendRequest RPC failed: {e.code()} - {e.details()}")

    except Exception as e:
        print(f"[SimpleHeadClient] An error occurred during client actions: {e}")


async def main(listen_port: int, scheduler_address: str):
    server_task = asyncio.create_task(run_server(listen_port))
    
    # Give the server a moment to start before client actions
    await asyncio.sleep(10) 

    # Perform client actions

    await perform_client_actions(scheduler_address)

    print("[SimpleTestHead] Client actions complete. Server will continue running.")
    print("[SimpleTestHead] Press Ctrl+C to stop the server.")
    
    try:
        await server_task # Keep main alive until server task is done (e.g., by cancellation)
    except KeyboardInterrupt:
        print("[SimpleTestHead] KeyboardInterrupt received in main. Stopping server task...")
        if not server_task.done():
            server_task.cancel()
            await server_task # Wait for server to clean up
        print("[SimpleTestHead] Exiting.")
    except asyncio.CancelledError:
        print("[SimpleTestHead] Main task cancelled (likely because server task finished or was cancelled).")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Simple Head Node: Server for Scheduler & Client to Scheduler")
    parser.add_argument("--listen_port", type=int, default=DEFAULT_HEAD_LISTEN_PORT,
                        help=f"Port for this simple head node's server to listen on (default: {DEFAULT_HEAD_LISTEN_PORT})")
    parser.add_argument("--scheduler_address", type=str, default=DEFAULT_SCHEDULER_ADDRESS,
                        help=f"Address (host:port) of the scheduler to send client requests to (default: {DEFAULT_SCHEDULER_ADDRESS})")
    args = parser.parse_args()

    try:
        asyncio.run(main(args.listen_port, args.scheduler_address))
    except KeyboardInterrupt:
        print("[SimpleTestHead] Application shutting down.")
    except Exception as e:
        print(f"[SimpleTestHead] Critical error in asyncio.run: {e}") 