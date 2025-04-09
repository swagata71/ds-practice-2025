import grpc
from concurrent import futures
import threading
import time
import os
import sys
import heapq
from dataclasses import dataclass, field

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
order_queue_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/order_queue'))
sys.path.insert(0, order_queue_grpc_path)

import order_queue_pb2
import order_queue_pb2_grpc

@dataclass(order=True)
class PrioritizedOrder:
    priority: int
    timestamp: float = field(compare=True)
    order_id: str = field(compare=False)

class OrderQueueService(order_queue_pb2_grpc.OrderQueueServiceServicer):
    def __init__(self):
        self._lock = threading.Lock()
        self._queue = []  # Priority queue using heapq

    def Enqueue(self, request, context):
        with self._lock:
            # Enhanced priority heuristic: higher amount + more items + premium user bonus
            priority_score = request.amount + request.itemCount

            if request.userType == "premium":
                priority_score += 5
            priority = -priority_score  # Negate for max-heap behavior using heapq

            order = PrioritizedOrder(priority, time.time(), request.orderId)
            heapq.heappush(self._queue, order)
            print(f"✅ Enqueued Order: {request.orderId} with priority {priority_score}")
            return order_queue_pb2.EnqueueResponse(success=True)

    def Dequeue(self, request, context):
        with self._lock:
            if self._queue:
                order = heapq.heappop(self._queue)
                print(f"🔄 Dequeued Order: {order.order_id}")
                return order_queue_pb2.DequeueResponse(orderId=order.order_id)
            else:
                print("⚠️ Queue empty.")
                return order_queue_pb2.DequeueResponse(orderId="")

def serve_queue_service():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    order_queue_pb2_grpc.add_OrderQueueServiceServicer_to_server(OrderQueueService(), server)
    server.add_insecure_port("[::]:50056")
    print("📦 Order Queue Service running on port 50056...")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve_queue_service()
