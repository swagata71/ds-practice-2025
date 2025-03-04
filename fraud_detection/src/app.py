import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc

import grpc
from concurrent import futures

# Create a class to define the server functions, derived from
# fraud_detection_pb2_grpc.HelloServiceServicer
class FraudDetectionService(fraud_detection_grpc.FraudServiceServicer):
    def CheckFraud(self, request, context):
        """ Fraud detection logic: Reject orders over $1000 """
        print(f"🔍 Checking fraud for Order {request.order_id} with Amount: {request.amount}")
        is_fraud = request.amount > 1000  # Mark orders over 1000 as fraudulent
        print(f"🚨 Fraud Status: {'Fraudulent' if is_fraud else 'Not Fraudulent'}")
        return fraud_detection.FraudResponse(is_fraud=is_fraud)
    
def serve():
    # Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor())
    # Add HelloService
    fraud_detection_grpc.add_FraudServiceServicer_to_server(FraudDetectionService(), server)
    # Listen on port 50051
    port = "50051"
    server.add_insecure_port("[::]:" + port)
    # Start the server
    server.start()
    print("✅ Fraud Detection Service running on port 50051")
    # Keep thread alive
    server.wait_for_termination()

if __name__ == '__main__':
    serve()