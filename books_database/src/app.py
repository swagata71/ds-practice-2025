import grpc
from concurrent import futures
import threading
import time
import os
import sys

# Vector clock utils and gRPC stubs
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
queue_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/order_queue'))
db_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/books_database'))
sys.path.insert(0, queue_grpc_path)
sys.path.insert(0, db_grpc_path)

import order_queue_pb2
import order_queue_pb2_grpc
import books_database_pb2
import books_database_pb2_grpc

lock = threading.Lock()

class BooksDatabaseServicer(books_database_pb2_grpc.BooksDatabaseServicer):
    def __init__(self, role, backup_peers=None):
        self.db = {}  # key-value store
        self.lock = threading.Lock()
        self.role = role
        self.backup_stubs = []

        if role == "primary" and backup_peers:
            for peer in backup_peers:
                host, port = peer.split(":")
                channel = grpc.insecure_channel(f"{host}:{port}")
                stub = books_database_pb2_grpc.BooksDatabaseStub(channel)
                self.backup_stubs.append(stub)

    # Common to both roles
    def Read(self, request, context):
        with self.lock:
            stock = self.db.get(request.title, 0)
        print(f"🔎 Read stock for {request.title}: {stock}")
        return books_database_pb2.ReadResponse(stock=stock)

    def DecrementStock(self, request, context):
        with self.lock:
            current = self.db.get(request.title, 0)
            if current >= request.quantity:
                self.db[request.title] = current - request.quantity
                print(f"Decremented {request.title} by {request.quantity}. Remaining: {self.db[request.title]}")
                return books_database_pb2.StockResponse(success=True, remaining=self.db[request.title])
            else:
                print(f"Not enough stock for {request.title}")
                return books_database_pb2.StockResponse(success=False, remaining=current)

    # Backup only
    def ReplicateWrite(self, request, context):
        with self.lock:
            self.db[request.title] = request.new_stock
            print(f"Backup wrote {request.title} → {request.new_stock}")
        return books_database_pb2.WriteResponse(success=True)

    # Primary only
    def Write(self, request, context):
        if self.role != "primary":
            context.abort(grpc.StatusCode.PERMISSION_DENIED, "Only primary can write")

        with self.lock:
            self.db[request.title] = request.new_stock
            print(f"Primary wrote {request.title} → {request.new_stock}")

        for stub in self.backup_stubs:
            try:
                stub.ReplicateWrite(request)
                print(f"Replicated {request.title} to backup")
            except Exception as e:
                print(f"Replication failed: {e}")

        return books_database_pb2.WriteResponse(success=True)

def serve():
    role = os.getenv("ROLE", "primary")
    backup_peers = os.getenv("BACKUP_PEERS", "").split(",") if role == "primary" else None
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    books_database_pb2_grpc.add_BooksDatabaseServicer_to_server(
        BooksDatabaseServicer(role, backup_peers), server
    )
    port = os.getenv("PORT", "50057")
    server.add_insecure_port(f"[::]:{port}")
    print(f"BooksDatabase {role} running on port {port}...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
