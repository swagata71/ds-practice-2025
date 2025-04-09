import os
import sys
import grpc
import time
import threading
from concurrent import futures
from queue import Queue

# Add path to import protobuf
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
order_executor_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/order_executor'))
sys.path.insert(0, order_executor_grpc_path)

import order_executor_pb2 as order_executor_pb2
import order_executor_pb2_grpc as order_executor_pb2_grpc

# Load environment variables
REPLICA_ID = int(os.getenv("REPLICA_ID", 0))
PORT = int(os.getenv("PORT", 50054))
PEERS = os.getenv("PEERS", "").split(',')

order_queue = Queue()
LEADER_ID = None

class ElectionService(order_executor_pb2_grpc.OrderExecutorServiceServicer):
    def __init__(self):
        self.is_leader = False
        self.running = True
        self.election_lock = threading.Lock()

    def StartElection(self, request, context):
        requester_id = request.replica_id
        print(f"Election requested by replica {requester_id}")

        if requester_id < REPLICA_ID:
            print(f"Responding to election from {requester_id} as I have higher ID {REPLICA_ID}")
            return order_executor_pb2.ElectionResponse(success=True, leader_id=self.replica_id)
        else:
            return order_executor_pb2.ElectionReply(success=False)

    def AnnounceLeader(self, request, context):
        global LEADER_ID
        LEADER_ID = request.replica_id
        self.is_leader = (LEADER_ID == REPLICA_ID)
        print(f"Replica {LEADER_ID} is now the leader.")
        return order_executor_pb2.Empty()

    def ExecuteOrder(self, request, context):
        print(f"Executing Order ID: {request.order_id}")
        return order_executor_pb2.ExecuteResponse(success=True)

def initiate_election():
    global LEADER_ID
    highest_id = REPLICA_ID
    for peer in PEERS:
        host, port = peer.split(':')
        try:
            channel = grpc.insecure_channel(f"{host}:{port}")
            stub = order_executor_pb2_grpc.OrderExecutorServiceStub(channel)
            response = stub.StartElection(order_executor_pb2.ElectionRequest(replica_id=REPLICA_ID))
            if response.success:
                print(f"Peer {peer} is alive with higher ID.")
                return  # Someone else will handle election
        except Exception as e:
            print(f"Failed to contact {peer}: {e}")

    # I am the leader
    LEADER_ID = REPLICA_ID
    print(f"Replica {REPLICA_ID} has become the leader!")
    for peer in PEERS:
        host, port = peer.split(':')
        try:
            channel = grpc.insecure_channel(f"{host}:{port}")
            stub = order_executor_pb2_grpc.OrderExecutorServiceStub(channel)
            stub.AnnounceLeader(order_executor_pb2.LeaderAnnouncement(replica_id=REPLICA_ID))
        except:
            pass

def start_order_processing(service):
    while True:
        time.sleep(5)
        if service.is_leader:
            print("Leader processing orders...")
            if not order_queue.empty():
                order = order_queue.get()
                print(f"Order is being executed: {order}")
            else:
                print("No orders in queue.")

if __name__ == '__main__':
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service = ElectionService()
    order_executor_pb2_grpc.add_OrderExecutorServiceServicer_to_server(service, server)
    server.add_insecure_port(f'[::]:{PORT}')
    server.start()
    print(f"Order Executor {REPLICA_ID} running on port {PORT}")

    # Begin election
    election_thread = threading.Thread(target=initiate_election)
    election_thread.start()

    # Start dummy order generation (for testing)
    def dummy_orders():
        i = 0
        while True:
            order_queue.put(f"Order_{i}")
            i += 1
            time.sleep(10)

    threading.Thread(target=dummy_orders, daemon=True).start()
    threading.Thread(target=start_order_processing, args=(service,), daemon=True).start()

    server.wait_for_termination()
