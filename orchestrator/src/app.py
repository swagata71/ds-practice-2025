import sys
import os
import threading

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_grpc
import transaction_verification_pb2 as transaction_pb2
import transaction_verification_pb2_grpc as transaction_pb2_grpc
import suggestions_pb2 as suggestions_pb2
import suggestions_pb2_grpc as suggestions_pb2_grpc

import grpc

# Import Flask.
# Flask is a web framework for Python.
# It allows you to build a web application quickly.
# For more information, see https://flask.palletsprojects.com/en/latest/
from flask import Flask, request, jsonify
from flask_cors import CORS
import json

# Create a simple Flask app.
app = Flask(__name__)
# Enable CORS for the app.
CORS(app, resources={r'/*': {'origins': '*'}})

# Connect to gRPC services
fraud_channel = grpc.insecure_channel('fraud_detection:50051')
fraud_stub = fraud_detection_grpc.FraudServiceStub(fraud_channel)

transaction_channel = grpc.insecure_channel('transaction_verification:50052')
transaction_stub = transaction_pb2_grpc.TransactionVerificationServiceStub(transaction_channel)

suggestions_channel = grpc.insecure_channel('suggestions:50053')
suggestions_stub = suggestions_pb2_grpc.SuggestionsServiceStub(suggestions_channel)


def check_fraud(order, results):
    """ Calls Fraud Detection Service """
    response = fraud_stub.CheckFraud(fraud_detection.FraudRequest(
        order_id=order["order_id"],
        user_id=order["user_id"],
        amount=order["amount"]
    ))
    results["fraudulent"] = response.is_fraud

def check_transaction(order):
    response = transaction_stub.VerifyTransaction(transaction_pb2.TransactionRequest(
        order_id=order["order_id"],
        user_id=order["user_id"],
        amount=order["amount"],
        payment_method=order["payment_method"]
    ))
    return response.is_valid, response.reason

def get_suggestions(purchased_books):
    response = suggestions_stub.GetSuggestions(suggestions_pb2.SuggestionRequest(
        purchased_books=purchased_books
    ))
    return response.suggested_books

@app.route('/checkout', methods=['POST'])
def checkout():
    """ Processes Checkout Request and Calls Fraud Detection """
    order = request.json  # Get order data from frontend
    
    # 🔹 Debugging: Print incoming request data
    print("🔍 Incoming Request Data:", order)

    # Check if order_id exists in request
    if "order_id" not in order:
        return jsonify({"error": "Missing order_id in request"}), 400
    
    results = {}
    fraud_thread = threading.Thread(target=check_fraud, args=(order, results))
    fraud_thread.start()
    fraud_thread.join()

    # Check fraud response
    if results.get("fraudulent", False):
        return jsonify({"status": "rejected", "reason": "Fraud detected"}), 400

    # Dummy response for now (extend later for other microservices)
    order_status_response = {
        'orderId': order["order_id"],
        'status': 'Order Approved',
        'suggestedBooks': [
            {'bookId': '123', 'title': 'The Best Book', 'author': 'Author 1'},
            {'bookId': '456', 'title': 'The Second Best Book', 'author': 'Author 2'}
        ]
    }

    return jsonify(order_status_response)


if __name__ == '__main__':
    # Run the app in debug mode to enable hot reloading.
    # This is useful for development.
    # The default port is 5000.
    app.run(host='0.0.0.0')
