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

        election_thread = threading.Thread(target=self.start_election)
        election_thread.start()

        executor_thread = threading.Thread(target=self.run)
        executor_thread.start()

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
                print(f"Replica {self.replica_id} is the new leader!")
        else:
            print(f"Replica {self.replica_id} waiting for leader announcement...")

    def StartElection(self, request, context):
        print(f"🗳️ Election thread started on replica {self.replica_id}")
        print(f"Received election request from {request.candidate_id}")
        if self.replica_id > request.candidate_id:
            print(f"Responding to election from {request.candidate_id} as I have higher ID {self.replica_id}")
            return order_executor_pb2.ElectionResponse(message="OK")
        return order_executor_pb2.ElectionResponse(message="ACK")

    def run(self):
        print(f"🏃 Executor loop started on replica {self.replica_id}")
        while True:
            if self.is_leader:
                print("I'm the leader. Trying to execute order...")
                try:
                    response = self.order_queue_stub.Dequeue(order_queue_pb2.Empty())
                    if response.orderId:
                        print(f"Executing order: {response.orderId}")
                        # Simulate read from order queue
                        # order_resp = self.order_queue_stub.Read(
                        #     order_queue_pb2.ReadRequest(key=response.orderId)
                        # )
                        try:
                            # Simulate read from books DB
                            stock_resp = self.books_db_stub.Read(
                                books_database_pb2.ReadRequest(title="book_A")
                            )
                            response = self.books_db_stub.DecrementStock(
                                books_database_pb2.StockRequest(title="book_A", quantity=1)
                                )
                            if response.success:
                                print(f"Stock decremented. Remaining: {response.remaining}")
                            else:
                                print("Not enough stock or book not found.")

                        except Exception as db_err:
                            print(f"DB operation failed: {db_err}")
                        
                    else:
                        print(" No orders to execute.")
                except Exception as e:
                    print(f"Failed to dequeue order: {e}")
            else:
                print("Not the leader. Waiting...")
            time.sleep(5)


def serve():
    replica_id = int(os.getenv("REPLICA_ID", "1"))
    port = int(os.getenv("REPLICA_PORT", "50054"))
    peer_list = os.getenv("PEERS", "").split(",")

    peers = []
    for peer in peer_list:
        if peer:
            peer_id, host, port = peer.split(":")
            peers.append({"id": int(peer_id), "host": host, "port": port})

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    order_executor_pb2_grpc.add_OrderExecutorServiceServicer_to_server(ExecutorService(replica_id, peers), server)
    server.add_insecure_port(f"[::]:{port}")
    print(f"🚀 Order Executor {replica_id} running on port {port}")
    print("🔧 Starting gRPC server...")
    server.start()
    print("✅ gRPC server started.")

    server.wait_for_termination()

if __name__ == "__main__":
    serve()
