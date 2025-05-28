import sys
import os
import threading
import grpc
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# OpenTelemetry imports
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# Set up OpenTelemetry resource
resource = Resource(attributes={SERVICE_NAME: "orchestrator"})

# Tracing setup
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://observability:4318/v1/traces"))
trace.get_tracer_provider().add_span_processor(span_processor)

# Metrics setup
metric_exporter = OTLPMetricExporter(endpoint="http://observability:4318/v1/metrics")
metric_reader = PeriodicExportingMetricReader(metric_exporter)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)
order_counter = meter.create_counter("orders_processed", unit="1", description="Number of orders processed")

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [Orchestrator] %(message)s')

# Setup gRPC stub paths
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
transaction_verification_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/transaction_verification'))
suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
order_queue_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/order_queue'))

sys.path.insert(0, fraud_detection_grpc_path)
sys.path.insert(0, transaction_verification_grpc_path)
sys.path.insert(0, suggestions_grpc_path)
sys.path.insert(0, order_queue_grpc_path)

# Import gRPC stubs
import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_pb2_grpc
import transaction_verification_pb2 as transaction_pb2
import transaction_verification_pb2_grpc as transaction_pb2_grpc
import suggestions_pb2 as suggestions_pb2
import suggestions_pb2_grpc as suggestions_pb2_grpc
import order_queue_pb2
import order_queue_pb2_grpc

# Flask app
app = Flask(__name__)
CORS(app, resources={r'/*': {'origins': '*'}})

# gRPC service connections
fraud_stub = fraud_detection_pb2_grpc.FraudServiceStub(grpc.insecure_channel('fraud_detection:50051'))
transaction_stub = transaction_pb2_grpc.TransactionVerificationServiceStub(grpc.insecure_channel('transaction_verification:50052'))
suggestions_stub = suggestions_pb2_grpc.SuggestionsServiceStub(grpc.insecure_channel('suggestions:50053'))
order_queue_stub = order_queue_pb2_grpc.OrderQueueServiceStub(grpc.insecure_channel("order_queue:50056"))

# ----- Transaction Verification Handler -----
def transaction_event_flow(order, result_holder, event):
    with tracer.start_as_current_span("transaction_event_flow"):
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
                event.set()
                return

            books_resp = transaction_stub.CheckBooks(transaction_pb2.EventRequest(order_id=order_id))
            logging.debug(f"CheckBooks updated clock: {books_resp.vector_clock}")
            if not books_resp.is_success:
                result_holder["transaction"] = (False, books_resp.message)
                event.set()
                return

            user_resp = transaction_stub.CheckUserFields(transaction_pb2.EventRequest(order_id=order_id))
            logging.debug(f"CheckUserFields updated clock: {user_resp.vector_clock}")
            if not user_resp.is_success:
                result_holder["transaction"] = (False, user_resp.message)
                event.set()
                return

            card_resp = transaction_stub.CheckCardFormat(transaction_pb2.EventRequest(order_id=order_id))
            logging.debug(f"CheckCardFormat updated clock: {card_resp.vector_clock}")
            if not card_resp.is_success:
                result_holder["transaction"] = (False, card_resp.message)
                event.set()
                return

            result_holder["transaction"] = (True, "Transaction Valid")
            event.set()

        except Exception as e:
            logging.error(f"transaction_event_flow failed: {str(e)}")
            result_holder["transaction"] = (False, "Transaction service encountered an internal error")
            event.set()

# ----- Fraud Detection Handler -----
def fraud_event_flow(order, result_holder, event):
    with tracer.start_as_current_span("fraud_event_flow"):
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
                event.set()
                return

            user_resp = fraud_stub.CheckUserFraud(fraud_detection.EventRequest(order_id=order_id))
            logging.debug(f"CheckUserFraud updated clock: {user_resp.vector_clock}")
            if not user_resp.is_success:
                result_holder["fraudulent"] = True
                event.set()
                return

            card_resp = fraud_stub.CheckCardFraud(fraud_detection.EventRequest(order_id=order_id))
            logging.debug(f"CheckCardFraud updated clock: {card_resp.vector_clock}")
            if not card_resp.is_success:
                result_holder["fraudulent"] = True
                event.set()
                return

            result_holder["fraudulent"] = False
            event.set()

        except Exception as e:
            logging.error(f"fraud_event_flow failed: {str(e)}")
            result_holder["fraudulent"] = True
            event.set()

# ----- Book Suggestions -----
def get_suggestions(order, result_holder, event):
    with tracer.start_as_current_span("get_suggestions"):
        try:
            order_id = order["order_id"]
            purchased_books = [item["name"] for item in order.get("items", [])]

            logging.debug(f"Function call_generate_suggestions(order_id = '{order_id}', order_data = {order}, result_dict = {result_holder})")
            response = suggestions_stub.GetSuggestions(suggestions_pb2.SuggestionRequest(
                purchased_books=purchased_books
            ))
            result_holder["suggested_books"] = response.suggested_books
            logging.debug(f"Final vector clock from Suggestions: {response.vector_clock}")
            event.set()
        except Exception as e:
            logging.error(f"get_suggestions failed: {str(e)}")
            result_holder["suggested_books"] = []
            event.set()

# ----- Checkout Route -----
@app.route('/checkout', methods=['POST'])
def checkout():
    order = request.json
    logging.debug(f"Incoming Request Data: {order}")

    if "order_id" not in order:
        return jsonify({"status": "rejected", "reason": "Missing order_id in request"}), 400

    with tracer.start_as_current_span("checkout_process"):
        results = {}
        fraud_done = threading.Event()
        transaction_done = threading.Event()
        suggestion_done = threading.Event()

        fraud_thread = threading.Thread(target=fraud_event_flow, args=(order, results, fraud_done))
        transaction_thread = threading.Thread(target=transaction_event_flow, args=(order, results, transaction_done))
        suggestions_thread = threading.Thread(target=get_suggestions, args=(order, results, suggestion_done))

        fraud_thread.start()
        transaction_thread.start()
        suggestions_thread.start()

        fraud_done.wait()
        if results.get("fraudulent", False):
            return jsonify({"status": "rejected", "reason": "Fraud detected"}), 400

        transaction_done.wait()
        is_valid, reason = results.get("transaction", (False, "Transaction check failed"))
        if not is_valid:
            return jsonify({"status": "rejected", "reason": reason}), 400

        suggestion_done.wait()
        suggested_books = results.get("suggested_books", [])

        try:
            order_id = order["order_id"]
            amount = float(order.get("amount", 0))
            item_count = len(order.get("items", []))
            user_type = order.get("user", {}).get("type", "regular")

            enqueue_resp = order_queue_stub.Enqueue(order_queue_pb2.OrderRequest(
                orderId=order_id,
                amount=amount,
                itemCount=item_count,
                userType=user_type
            ))

            if not enqueue_resp.success:
                return jsonify({"status": "rejected", "reason": "Failed to enqueue order"}), 500

            logging.info(f"Order {order_id} enqueued successfully.")
            order_counter.add(1, {"user_type": user_type, "status": "approved"})

        except Exception as e:
            logging.error(f"Enqueue failed: {str(e)}")
            return jsonify({"status": "rejected", "reason": "Internal error during enqueue"}), 500

        return jsonify({
            "orderId": order["order_id"],
            "status": "Order Approved",
            "suggestedBooks": [{"title": book} for book in suggested_books],
        })

# ----- Run -----
if __name__ == '__main__':
    app.run(host='0.0.0.0')
