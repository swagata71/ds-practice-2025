import sys
import os
import grpc
from concurrent import futures
import threading
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [FraudDetection] %(message)s')

FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
fraud_detection_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/fraud_detection'))
sys.path.insert(0, fraud_detection_grpc_path)

import fraud_detection_pb2 as fraud_detection
import fraud_detection_pb2_grpc as fraud_detection_pb2_grpc

# In-memory store for order data and vector clocks
order_data_store = {}
vector_clocks = {}
lock = threading.Lock()
service_id = "fraud_detection"

def increment_vc(vc, sid):
    vc = vc.copy()
    vc[sid] = vc.get(sid, 0) + 1
    return vc

def compare_vcs(local_vc, final_vc):
    for k in final_vc:
        if local_vc.get(k, 0) > final_vc[k]:
            return False
    return True

class FraudDetectionService(fraud_detection_pb2_grpc.FraudServiceServicer):
    def InitOrder(self, request, context):
        with lock:
            order_data_store[request.order_id] = {
                "user_id": request.user_id,
                "amount": request.amount
            }
            vector_clocks[request.order_id] = {service_id: 1}
            logging.debug(f"InitOrder updated VC for order {request.order_id}: {vector_clocks[request.order_id]}")
            return fraud_detection.InitOrderResponse(
                success=True,
                message="Order initialized",
                vector_clock=vector_clocks[request.order_id]
            )

    def CheckUserFraud(self, request, context):
        with lock:
            order = order_data_store.get(request.order_id)
            if not order:
                return fraud_detection.EventResponse(
                    is_success=False,
                    message="Order not found",
                    vector_clock={}
                )
            vector_clocks[request.order_id] = increment_vc(vector_clocks[request.order_id], service_id)
            logging.debug(f"CheckUserFraud updated VC for order {request.order_id}: {vector_clocks[request.order_id]}")
            return fraud_detection.EventResponse(
                is_success=True,
                message="User data not fraudulent",
                vector_clock=vector_clocks[request.order_id]
            )

    def CheckCardFraud(self, request, context):
        with lock:
            order = order_data_store.get(request.order_id)
            if not order:
                return fraud_detection.EventResponse(
                    is_success=False,
                    message="Order not found",
                    vector_clock={}
                )
            vector_clocks[request.order_id] = increment_vc(vector_clocks[request.order_id], service_id)
            is_fraud = order["amount"] > 1000
            logging.debug(f"CheckCardFraud updated VC for order {request.order_id}: {vector_clocks[request.order_id]}")
            logging.debug(f"CheckCardFraud FRAUD STATUS for order {request.order_id}: {'FRAUD' if is_fraud else 'OK'}")
            return fraud_detection.EventResponse(
                is_success=not is_fraud,
                message="Fraudulent card" if is_fraud else "Card data clean",
                vector_clock=vector_clocks[request.order_id]
            )

    def ClearOrder(self, request, context):
        with lock:
            local_vc = vector_clocks.get(request.order_id, {})
            if compare_vcs(local_vc, request.final_vector_clock):
                order_data_store.pop(request.order_id, None)
                vector_clocks.pop(request.order_id, None)
                logging.debug(f"ClearOrder succeeded for order {request.order_id}")
                return fraud_detection.ClearOrderResponse(status="Cleared")
            else:
                logging.debug(f"ClearOrder failed for order {request.order_id}. Local VC: {local_vc}, Final VC: {request.final_vector_clock}")
                return fraud_detection.ClearOrderResponse(status="VC mismatch - not cleared")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    fraud_detection_pb2_grpc.add_FraudServiceServicer_to_server(FraudDetectionService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    logging.info("✅ Fraud Detection Service running on port 50051")
    server.wait_for_termination()

if __name__ == '__main__':
    
    logging.info("Starting Fraud Detection Service...")
    serve()