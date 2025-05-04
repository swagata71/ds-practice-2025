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

class OrderExecutor:
    def __init__(self, replica_id, order_queue_host="order_queue", order_queue_port=50056, db_host="books_database_1", db_port=50057):
        self.replica_id = replica_id
        self.order_queue_stub = self.connect_order_queue(order_queue_host, order_queue_port)
        self.db_stub = self.connect_books_database(db_host, db_port)

    def connect_order_queue(self, host, port):
        channel = grpc.insecure_channel(f"{host}:{port}")
        return order_queue_pb2_grpc.OrderQueueServiceStub(channel)

    def connect_books_database(self, host, port):
        channel = grpc.insecure_channel(f"{host}:{port}")
        return books_database_pb2_grpc.BooksDatabaseStub(channel)

    def execute_orders(self):
        while True:
            response = self.order_queue_stub.Dequeue(order_queue_pb2.Empty())
            order_id = response.orderId
            if order_id:
                print(f"⚙️ Executing Order: {order_id}")
                # Read-Modify-Write logic
                book_id = "book123"
                read_response = self.db_stub.Read(books_database_pb2.ReadRequest(book_id=book_id))
                current_stock = read_response.stock

                if current_stock > 0:
                    new_stock = current_stock - 1
                    self.db_stub.Write(books_database_pb2.WriteRequest(book_id=book_id, stock=new_stock))
                    print(f"Order {order_id}: Decremented stock of {book_id} to {new_stock}")
                else:
                    print(f"Order {order_id}: Book {book_id} is out of stock!")
            else:
                print("🕒 Waiting for orders...")
                time.sleep(2)

def serve():
    replica_id = int(os.environ.get("REPLICA_ID", 1))
    order_executor = OrderExecutor(replica_id)
    print(f"🚀 Order Executor {replica_id} running...")
    order_executor.execute_orders()

if __name__ == '__main__':
    serve()