import sys
import os
import grpc
from concurrent import futures
import threading
#all clear
# Import the gRPC stubs (update path only if needed)
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)

import transaction_verification_pb2 as transaction_pb2
import transaction_verification_pb2_grpc as transaction_pb2_grpc

# In-memory storage for order data and vector clocks
order_data_store = {}
vector_clocks = {}
lock = threading.Lock()
service_id = "transaction_verification"

# Vector Clock Utility
def increment_vc(vc, service_id):
    vc = vc.copy()
    vc[service_id] = vc.get(service_id, 0) + 1
    return vc

def compare_vcs(local_vc, remote_vc):
    for k in remote_vc:
        if local_vc.get(k, 0) > remote_vc[k]:
            return False
    return True

class TransactionVerificationService(transaction_pb2_grpc.TransactionVerificationServiceServicer):
    def InitOrder(self, request, context):
        with lock:
            order_data_store[request.order_id] = {
                "user_data": request.user_data,
                "books": request.books,
                "credit_card": request.credit_card
            }
            vector_clocks[request.order_id] = {service_id: 1}
            print(f"[InitOrder] Order {request.order_id} initialized with VC: {vector_clocks[request.order_id]}")
            return transaction_pb2.InitOrderResponse(
                success=True,
                message="Order initialized",
                vector_clock=vector_clocks[request.order_id]
            )

    def CheckBooks(self, request, context):
        with lock:
            order = order_data_store.get(request.order_id)
            if not order:
                return transaction_pb2.EventResponse(
                    is_success=False, message="Order not found", vector_clock={}
                )

            books = order["books"]
            vector_clocks[request.order_id] = increment_vc(vector_clocks[request.order_id], service_id)
            if not books:
                return transaction_pb2.EventResponse(
                    is_success=False,
                    message="Book list is empty",
                    vector_clock=vector_clocks[request.order_id]
                )

            print(f"[CheckBooks] Order {request.order_id} passed book check.")
            return transaction_pb2.EventResponse(
                is_success=True,
                message="Books are valid",
                vector_clock=vector_clocks[request.order_id]
            )

    def CheckUserFields(self, request, context):
        with lock:
            order = order_data_store.get(request.order_id)
            if not order:
                return transaction_pb2.EventResponse(
                    is_success=False, message="Order not found", vector_clock={}
                )

            user_data = order["user_data"]
            vector_clocks[request.order_id] = increment_vc(vector_clocks[request.order_id], service_id)
            required_fields = ["name", "contact", "address"]

            for field in required_fields:
                if not user_data.get(field):
                    return transaction_pb2.EventResponse(
                        is_success=False,
                        message=f"Missing required user field: {field}",
                        vector_clock=vector_clocks[request.order_id]
                    )

            print(f"[CheckUserFields] Order {request.order_id} passed user field check.")
            return transaction_pb2.EventResponse(
                is_success=True,
                message="All user fields are valid",
                vector_clock=vector_clocks[request.order_id]
            )

    def CheckCardFormat(self, request, context):
        with lock:
            order = order_data_store.get(request.order_id)
            if not order:
                return transaction_pb2.EventResponse(
                    is_success=False, message="Order not found", vector_clock={}
                )

            card = order["credit_card"]
            vector_clocks[request.order_id] = increment_vc(vector_clocks[request.order_id], service_id)
            if not card or len(card) != 16 or not card.isdigit():
                return transaction_pb2.EventResponse(
                    is_success=False,
                    message="Invalid credit card format",
                    vector_clock=vector_clocks[request.order_id]
                )

            print(f"[CheckCardFormat] Order {request.order_id} passed credit card format check.")
            return transaction_pb2.EventResponse(
                is_success=True,
                message="Credit card format is valid",
                vector_clock=vector_clocks[request.order_id]
            )

    def ClearOrder(self, request, context):
        with lock:
            local_vc = vector_clocks.get(request.order_id, {})
            if compare_vcs(local_vc, request.final_vector_clock):
                order_data_store.pop(request.order_id, None)
                vector_clocks.pop(request.order_id, None)
                print(f"[ClearOrder] Order {request.order_id} cleared successfully.")
                return transaction_pb2.ClearOrderResponse(status="Cleared")
            else:
                print(f"[ClearOrder] Order {request.order_id} NOT cleared. Local VC: {local_vc}, Final VC: {request.final_vector_clock}")
                return transaction_pb2.ClearOrderResponse(status="Vector clock mismatch - not cleared.")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_pb2_grpc.add_TransactionVerificationServiceServicer_to_server(TransactionVerificationService(), server)
    server.add_insecure_port("[::]:50052")
    server.start()
    print("Transaction Verification Service running on port 50052....")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()

