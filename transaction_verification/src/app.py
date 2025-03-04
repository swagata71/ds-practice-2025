import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
sys.path.insert(0, transaction_verification_grpc_path)

import grpc
from concurrent import futures
import transaction_verification_pb2 as transaction_pb2
import transaction_verification_pb2_grpc as transaction_pb2_grpc

class TransactionVerificationService(transaction_pb2_grpc.TransactionVerificationServiceServicer):
    def VerifyTransaction(self, request, context):
        if request.amount <= 0:
            return transaction_pb2.TransactionResponse(is_valid=False, reason="Invalid transaction amount.")
        if not request.payment_method:
            return transaction_pb2.TransactionResponse(is_valid=False, reason="Missing payment method.")
        if request.payment_method == "credit_card":
            if not request.credit_card or len(request.credit_card) < 16:
                return transaction_pb2.TransactionResponse(is_valid=False, reason="Invalid credit card number. Must be at least 16 digits.")
        
        return transaction_pb2.TransactionResponse(is_valid=True, reason="Transaction is valid.")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    transaction_pb2_grpc.add_TransactionVerificationServiceServicer_to_server(TransactionVerificationService(), server)
    server.add_insecure_port("[::]:50052")
    server.start()
    print("Transaction Verification Service running on port 50052....")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
