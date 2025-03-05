import sys
import os

# This set of lines are needed to import the gRPC stubs.
# The path of the stubs is relative to the current file, or absolute inside the container.
# Change these lines only if strictly needed.
FILE = __file__ if '__file__' in globals() else os.getenv("PYTHONFILE", "")
suggestions_grpc_path = os.path.abspath(os.path.join(FILE, '../../../utils/pb/suggestions'))
sys.path.insert(0, suggestions_grpc_path)

import grpc
from concurrent import futures
import suggestions_pb2 as suggestions_pb2
import suggestions_pb2_grpc as suggestions_pb2_grpc

BOOK_SUGGESTIONS = {
    "Book A": ["Book C", "Book D"],
    "Book B": ["Book E", "Book F"],
    "Book K": ["Book G", "Book H"],
    "Book L": ["Book I", "Book J"],
}
class SuggestionsService(suggestions_pb2_grpc.SuggestionsServiceServicer):
    def GetSuggestions(self, request, context):
        suggested_books = set()
        for book in request.purchased_books:
            suggested_books.update(BOOK_SUGGESTIONS.get(book, []))
        return suggestions_pb2.SuggestionResponse(suggested_books=list(suggested_books))

def serve():
    server = grpc.server(futures.ThreadPoolExecutor())
    suggestions_pb2_grpc.add_SuggestionsServiceServicer_to_server(SuggestionsService(), server)
    server.add_insecure_port("[::]:50053")
    server.start()
    print("Suggestions Service running on port 50053...")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
