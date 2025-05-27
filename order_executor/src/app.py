import os
import sys
import time
import threading
import grpc
from concurrent import futures
from dotenv import load_dotenv

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
proto_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/order_executor'))
sys.path.insert(0, proto_path)

order_queue_proto_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/order_queue'))
sys.path.insert(0, order_queue_proto_path)

books_db_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/books_database'))
sys.path.insert(0, books_db_path)

import books_database_pb2
import books_database_pb2_grpc
import order_executor_pb2
import order_executor_pb2_grpc
import order_queue_pb2
import order_queue_pb2_grpc

load_dotenv()

class ExecutorService(order_executor_pb2_grpc.OrderExecutorServiceServicer):
    def __init__(self, replica_id, peers):
        self.replica_id = replica_id
        self.peers = peers
        self.is_leader = False
        self.leader_id = None
        self.lock = threading.Lock()

        self.order_queue_channel = grpc.insecure_channel("order_queue:50056")
        self.order_queue_stub = order_queue_pb2_grpc.OrderQueueServiceStub(self.order_queue_channel)
        self.books_db_channel = grpc.insecure_channel("books_primary:50060")
        self.books_db_stub = books_database_pb2_grpc.BooksDatabaseStub(self.books_db_channel)

        print(f"[Init] ExecutorService for Replica {self.replica_id} initialized.")
        peer_list_str = [f"{p['id']}:{p['host']}:{p['port']}" for p in self.peers]
        print(f"[Init] Peers configured: {peer_list_str}")

        threading.Thread(target=self.delayed_start_election_with_retries, daemon=True).start()

    def delayed_start_election_with_retries(self):
        max_retries = 10
        retry_interval = 2
        for attempt in range(max_retries):
            print(f"[Startup] Replica {self.replica_id} trying to connect to peers (attempt {attempt+1})...")
            all_reachable = True
            for peer in self.peers:
                try:
                    channel = grpc.insecure_channel(f"{peer['host']}:{peer['port']}")
                    grpc.channel_ready_future(channel).result(timeout=1)
                except Exception:
                    all_reachable = False
                    break
            if all_reachable:
                print(f"[Startup] All peers reachable. Starting election...")
                self.start_election()
                return
            time.sleep(retry_interval)
        print(f"[Startup] Could not reach all peers after {max_retries} attempts. Starting election anyway.")
        self.start_election()

    def start_election(self):
        print(f"Replica {self.replica_id} initiating election...")
        higher_ids = [peer for peer in self.peers if peer['id'] > self.replica_id]
        received_ok = False

        for peer in higher_ids:
            try:
                channel = grpc.insecure_channel(f"{peer['host']}:{peer['port']}")
                stub = order_executor_pb2_grpc.OrderExecutorServiceStub(channel)
                response = stub.StartElection(order_executor_pb2.ElectionRequest(sender_id=self.replica_id))
                print(f"Received OK from Replica {peer['id']}")
                received_ok = True
            except Exception as e:
                print(f"Failed to contact {peer['host']}:{peer['port']}: {e}")

        if not received_ok:
            with self.lock:
                self.is_leader = True
                self.leader_id = self.replica_id
                print(f"[LeaderElection] Replica {self.replica_id} is now the LEADER")

                for peer in self.peers:
                    try:
                        channel = grpc.insecure_channel(f"{peer['host']}:{peer['port']}")
                        stub = order_executor_pb2_grpc.OrderExecutorServiceStub(channel)
                        stub.AnnounceLeader(order_executor_pb2.LeaderAnnouncement(leader_id=self.replica_id))
                    except Exception as e:
                        print(f"Could not inform peer {peer['id']} about new leader: {e}")
                self.run()

    def StartElection(self, request, context):
        print(f"🗳️ Election thread started on replica {self.replica_id}")
        print(f"Received election request from {request.sender_id}")
        if self.replica_id > request.sender_id:
            print(f"Responding to election from {request.sender_id} as I have higher ID {self.replica_id}")
            return order_executor_pb2.ElectionResponse(acknowledged=True)
        return order_executor_pb2.ElectionResponse(acknowledged=False)

    def AnnounceLeader(self, request, context):
        with self.lock:
            self.leader_id = request.leader_id
            self.is_leader = (self.replica_id == request.leader_id)
            print(f"📢 Leader announced: Replica {self.leader_id}")
        return order_executor_pb2.Ack(received=True)

    def run(self):
        while True:
            try:
                order = self.order_queue_stub.Dequeue(order_queue_pb2.Empty())
                if hasattr(order, "order_id") and order.order_id:
                    print(f"[OrderExecutor {self.replica_id}] Executing order {order.order_id}")
                else:
                    print(f"[OrderExecutor {self.replica_id}] Queue is empty.")
            except Exception as e:
                print(f"[OrderExecutor {self.replica_id}] Failed to dequeue: {e}")
            time.sleep(5)

def serve():
    replica_id = int(os.getenv("REPLICA_ID", "1"))
    port = int(os.getenv("REPLICA_PORT", "50054"))
    peer_list = os.getenv("PEERS", "").split(",")

    peers = []
    for peer in peer_list:
        if peer:
            peer_id, host, port_str = peer.split(":")
            peers.append({"id": int(peer_id), "host": host, "port": port_str})

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    # Prepare the service but don't instantiate yet
    service_placeholder = order_executor_pb2_grpc.OrderExecutorServiceServicer()

    order_executor_pb2_grpc.add_OrderExecutorServiceServicer_to_server(service_placeholder, server)
    server.add_insecure_port(f"[::]:{port}")
    print(f"🚀 Order Executor {replica_id} binding to port {port}")
    print("🔧 Starting gRPC server...")
    server.start()
    print("✅ gRPC server started.")

    # Instantiate the service after the server is listening
    service = ExecutorService(replica_id, peers)

    # Replace the placeholder (server already running)
    server.stop(0)  # Stop the previous placeholder service immediately
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    order_executor_pb2_grpc.add_OrderExecutorServiceServicer_to_server(service, server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    server.wait_for_termination()


if __name__ == "__main__":
    serve()
