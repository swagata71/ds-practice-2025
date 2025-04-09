import sys
import os
import threading
import grpc
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [Orchestrator] %(message)s')

# Setup gRPC stub paths
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))

sys.path.insert(0, fraud_detection_grpc_path)
sys.path.insert(0, transaction_verification_grpc_path)
sys.path.insert(0, suggestions_grpc_path)

# Import gRPC stubs
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_pb2_grpc
import transaction_verification_pb2 as transaction_pb2
import transaction_verification_pb2_grpc as transaction_pb2_grpc
import suggestions_pb2 as suggestions_pb2
import suggestions_pb2_grpc as suggestions_pb2_grpc

# Flask app
app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})

# gRPC service connections
fraud_stub = fraud_detection_pb2_grpc.FraudServiceStub(grpc.insecure_channel('fraud_detection:50051'))
transaction_stub = transaction_pb2_grpc.TransactionVerificationServiceStub(grpc.insecure_channel('transaction_verification:50052'))
suggestions_stub = suggestions_pb2_grpc.SuggestionsServiceStub(grpc.insecure_channel('suggestions:50053'))

# ----- Transaction Verification Handler -----

def transaction_event_flow(order, result_holder):
    try:
        order_id = order["order_id"]
        user_data = {
            "name": order["user"]["name"],
            "contact": order["user"]["contact"],
            "address": order["billingAddress"]["street"]
        }
        books = [item["name"] for item in order.get("items", [])]
        credit_card = str(order["creditCard"]["number"]).replace(" ", "").replace("-", "")

        init_response = transaction_stub.InitOrder(transaction_pb2.InitOrderRequest(
            order_id=order_id,
            user_data=user_data,
            books=books,
            credit_card=credit_card
        ))
        logging.debug(f"InitOrder updated clock: {init_response.vector_clock}")

        if not init_response.success:
            result_holder["transaction"] = (False, init_response.message)
            return

        books_resp = transaction_stub.CheckBooks(transaction_pb2.EventRequest(order_id=order_id))
        logging.debug(f"CheckBooks updated clock: {books_resp.vector_clock}")
        if not books_resp.is_success:
            result_holder["transaction"] = (False, books_resp.message)
            return

        user_resp = transaction_stub.CheckUserFields(transaction_pb2.EventRequest(order_id=order_id))
        logging.debug(f"CheckUserFields updated clock: {user_resp.vector_clock}")
        if not user_resp.is_success:
            result_holder["transaction"] = (False, user_resp.message)
            return

        card_resp = transaction_stub.CheckCardFormat(transaction_pb2.EventRequest(order_id=order_id))
        logging.debug(f"CheckCardFormat updated clock: {card_resp.vector_clock}")
        if not card_resp.is_success:
            result_holder["transaction"] = (False, card_resp.message)
            return

        result_holder["transaction"] = (True, "Transaction Valid")

    except Exception as e:
        logging.debug(f"Exception in transaction_event_flow: {str(e)}")
        result_holder["transaction"] = (False, f"Exception: {str(e)}")

# ----- Fraud Detection Handler -----

def fraud_event_flow(order, result_holder):
    try:
        order_id = order["order_id"]
        user_id = order["user_id"]
        amount = order["amount"]

        init_response = fraud_stub.InitOrder(fraud_detection.InitOrderRequest(
            order_id=order_id,
            user_id=user_id,
            amount=amount
        ))
        logging.debug(f"InitOrder updated clock: {init_response.vector_clock}")

        if not init_response.success:
            result_holder["fraudulent"] = True
            return

        user_resp = fraud_stub.CheckUserFraud(fraud_detection.EventRequest(order_id=order_id))
        logging.debug(f"CheckUserFraud updated clock: {user_resp.vector_clock}")
        if not user_resp.is_success:
            result_holder["fraudulent"] = True
            return

        card_resp = fraud_stub.CheckCardFraud(fraud_detection.EventRequest(order_id=order_id))
        logging.debug(f"CheckCardFraud updated clock: {card_resp.vector_clock}")
        if not card_resp.is_success:
            result_holder["fraudulent"] = True
            return

        result_holder["fraudulent"] = False

    except Exception as e:
        logging.debug(f"Exception in fraud_event_flow: {str(e)}")
        result_holder["fraudulent"] = True

# ----- Book Suggestions -----

def get_suggestions(purchased_books):
    response = suggestions_stub.GetSuggestions(suggestions_pb2.SuggestionRequest(
        purchased_books=purchased_books
    ))
    return response.suggested_books

# ----- Checkout Route -----

@app.route('/checkout', methods=['POST'])
def checkout():
    order = request.json
    logging.debug(f"Incoming Request Data: {order}")

    if "order_id" not in order:
        return jsonify({"error": "Missing order_id in request"}), 400

    purchased_books = [item["name"] for item in order.get("items", [])]
    results = {}

    fraud_thread = threading.Thread(target=fraud_event_flow, args=(order, results))
    transaction_thread = threading.Thread(target=transaction_event_flow, args=(order, results))
    suggestions_thread = threading.Thread(target=lambda: results.update({"suggested_books": get_suggestions(purchased_books)}))

    fraud_thread.start()
    transaction_thread.start()
    suggestions_thread.start()

    fraud_thread.join()
    transaction_thread.join()
    suggestions_thread.join()

    is_valid, reason = results.get("transaction", (False, "Transaction check failed"))
    suggested_books = results.get("suggested_books", [])

    if results.get("fraudulent", False):
        return jsonify({"status": "rejected", "reason": "Fraud detected"}), 400

    if not is_valid:
        return jsonify({"status": "rejected", "reason": reason}), 400

    return jsonify({
        "orderId": order["order_id"],
        "status": "Order Approved",
        "suggestedBooks": [{"title": book} for book in suggested_books],
    })

# ----- Run -----

if __name__ == '__main__':
    app.run(host='0.0.0.0')
