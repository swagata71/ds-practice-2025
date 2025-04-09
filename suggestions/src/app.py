import sys
import os
import grpc
from concurrent import futures
import threading
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [Suggestions] %(message)s')

# Setup gRPC stub path
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestions_grpc_path)

# Import gRPC stubs
import suggestions_pb2 as suggestions_pb2
import suggestions_pb2_grpc as suggestions_pb2_grpc

# Constants
BOOK_SUGGESTIONS = {
    "Book A": ["Book C", "Book D"],
    "Book B": ["Book E", "Book F"],
    "Book K": ["Book G", "Book H"],
    "Book L": ["Book I", "Book J"],
}

# Vector clock management
lock = threading.Lock()
vector_clocks = {}
service_id = "suggestions"

def increment_vc(order_id):
    with lock:
        vc = vector_clocks.get(order_id, {})
        vc[service_id] = vc.get(service_id, 0) + 1
        vector_clocks[order_id] = vc
        return vc

class SuggestionsService(suggestions_pb2_grpc.SuggestionsServiceServicer):
    def GetSuggestions(self, request, context):
        suggested_books = set()
        for book in request.purchased_books:
            suggested_books.update(BOOK_SUGGESTIONS.get(book, []))

        order_id = context.invocation_metadata()[-1].value if context.invocation_metadata() else "unknown"
        vc = increment_vc(order_id)

        logging.debug(f"[GetSuggestions] Order {order_id}, VC updated: {vc}")
        return suggestions_pb2.SuggestionResponse(
            suggested_books=list(suggested_books),
            vector_clock=vc
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    suggestions_pb2_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)
    server.add_insecure_port("[::]:50053")
    server.start()
    logging.info("Suggestions Service running on port 50053...")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
