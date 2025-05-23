# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import order_executor_pb2 as order__executor_dot_order__executor__pb2


class OrderExecutorServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.StartElection = channel.unary_unary(
                '/order_executor.OrderExecutorService/StartElection',
                request_serializer=order__executor_dot_order__executor__pb2.ElectionRequest.SerializeToString,
                response_deserializer=order__executor_dot_order__executor__pb2.ElectionResponse.FromString,
                )
        self.AnnounceLeader = channel.unary_unary(
                '/order_executor.OrderExecutorService/AnnounceLeader',
                request_serializer=order__executor_dot_order__executor__pb2.LeaderAnnouncement.SerializeToString,
                response_deserializer=order__executor_dot_order__executor__pb2.Ack.FromString,
                )
        self.DequeueOrder = channel.unary_unary(
                '/order_executor.OrderExecutorService/DequeueOrder',
                request_serializer=order__executor_dot_order__executor__pb2.OrderRequest.SerializeToString,
                response_deserializer=order__executor_dot_order__executor__pb2.OrderResponse.FromString,
                )


class OrderExecutorServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def StartElection(self, request, context):
        """Called by a lower ID replica to start an election
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def AnnounceLeader(self, request, context):
        """Called to announce who won the election
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def DequeueOrder(self, request, context):
        """Called by the leader to dequeue and process an order
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_OrderExecutorServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'StartElection': grpc.unary_unary_rpc_method_handler(
                    servicer.StartElection,
                    request_deserializer=order__executor_dot_order__executor__pb2.ElectionRequest.FromString,
                    response_serializer=order__executor_dot_order__executor__pb2.ElectionResponse.SerializeToString,
            ),
            'AnnounceLeader': grpc.unary_unary_rpc_method_handler(
                    servicer.AnnounceLeader,
                    request_deserializer=order__executor_dot_order__executor__pb2.LeaderAnnouncement.FromString,
                    response_serializer=order__executor_dot_order__executor__pb2.Ack.SerializeToString,
            ),
            'DequeueOrder': grpc.unary_unary_rpc_method_handler(
                    servicer.DequeueOrder,
                    request_deserializer=order__executor_dot_order__executor__pb2.OrderRequest.FromString,
                    response_serializer=order__executor_dot_order__executor__pb2.OrderResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'order_executor.OrderExecutorService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class OrderExecutorService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def StartElection(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/order_executor.OrderExecutorService/StartElection',
            order__executor_dot_order__executor__pb2.ElectionRequest.SerializeToString,
            order__executor_dot_order__executor__pb2.ElectionResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def AnnounceLeader(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/order_executor.OrderExecutorService/AnnounceLeader',
            order__executor_dot_order__executor__pb2.LeaderAnnouncement.SerializeToString,
            order__executor_dot_order__executor__pb2.Ack.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def DequeueOrder(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/order_executor.OrderExecutorService/DequeueOrder',
            order__executor_dot_order__executor__pb2.OrderRequest.SerializeToString,
            order__executor_dot_order__executor__pb2.OrderResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
