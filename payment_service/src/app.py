import time
from concurrent import futures
import grpc
import os

from dotenv import load_dotenv
load_dotenv()

# Add path to generated gRPC classes
import sys
sys.path.insert(0, "/app/utils/pb/payment_service")

import payment_service_pb2
import payment_service_pb2_grpc

class PaymentService(payment_service_pb2_grpc.PaymentServiceServicer):
    def PrepareOrder(self, request, context):
        print(f"📥 Received PREPARE for order {request.order_id}")
        # Simulate processing delay or checks
        time.sleep(1)
        print(f"✅ PREPARE successful for order {request.order_id}")
        return payment_service_pb2.Ack(success=True)

    def CommitOrder(self, request, context):
        print(f"📥 Received COMMIT for order {request.order_id}")
        # Simulate commit logic (dummy)
        time.sleep(1)
        print(f"💰 Payment COMMITTED for order {request.order_id}")
        return payment_service_pb2.Ack(success=True)

    def AbortOrder(self, request, context):
        print(f"📥 Received ABORT for order {request.order_id}")
        # Simulate rollback (dummy)
        time.sleep(1)
        print(f"❌ Payment ABORTED for order {request.order_id}")
        return payment_service_pb2.Ack(success=True)

def serve():
    port = os.getenv("PORT", "50058")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    payment_service_pb2_grpc.add_PaymentServiceServicer_to_server(PaymentService(), server)
    server.add_insecure_port(f"[::]:{port}")
    print(f"🚀 Payment Service running on port {port}")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
