# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc
import warnings

from . import common_pb2 as common__pb2
from google.protobuf import empty_pb2 as google_dot_protobuf_dot_empty__pb2
from . import replica_service_pb2 as replica__service__pb2

GRPC_GENERATED_VERSION = '1.64.1'
GRPC_VERSION = grpc.__version__
EXPECTED_ERROR_RELEASE = '1.65.0'
SCHEDULED_RELEASE_DATE = 'June 25, 2024'
_version_not_supported = False

try:
    from grpc._utilities import first_version_is_lower
    _version_not_supported = first_version_is_lower(GRPC_VERSION, GRPC_GENERATED_VERSION)
except ImportError:
    _version_not_supported = True

if _version_not_supported:
    warnings.warn(
        f'The grpc package installed is at version {GRPC_VERSION},'
        + f' but the generated code in replica_service_pb2_grpc.py depends on'
        + f' grpcio>={GRPC_GENERATED_VERSION}.'
        + f' Please upgrade your grpc module to grpcio>={GRPC_GENERATED_VERSION}'
        + f' or downgrade your generated code using grpcio-tools<={GRPC_VERSION}.'
        + f' This warning will become an error in {EXPECTED_ERROR_RELEASE},'
        + f' scheduled for release on {SCHEDULED_RELEASE_DATE}.',
        RuntimeWarning
    )


class WorkerServiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.SendRequest = channel.unary_stream(
                '/protos.WorkerService/SendRequest',
                request_serializer=replica__service__pb2.ReplicaRequest.SerializeToString,
                response_deserializer=replica__service__pb2.ReplicaReply.FromString,
                _registered_method=True)
        self.Ping = channel.unary_unary(
                '/protos.WorkerService/Ping',
                request_serializer=google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
                response_deserializer=common__pb2.Ack.FromString,
                _registered_method=True)


class WorkerServiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def SendRequest(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Ping(self, request, context):
        """Ping from the workerNode
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_WorkerServiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'SendRequest': grpc.unary_stream_rpc_method_handler(
                    servicer.SendRequest,
                    request_deserializer=replica__service__pb2.ReplicaRequest.FromString,
                    response_serializer=replica__service__pb2.ReplicaReply.SerializeToString,
            ),
            'Ping': grpc.unary_unary_rpc_method_handler(
                    servicer.Ping,
                    request_deserializer=google_dot_protobuf_dot_empty__pb2.Empty.FromString,
                    response_serializer=common__pb2.Ack.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'protos.WorkerService', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))
    server.add_registered_method_handlers('protos.WorkerService', rpc_method_handlers)


 # This class is part of an EXPERIMENTAL API.
class WorkerService(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def SendRequest(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(
            request,
            target,
            '/protos.WorkerService/SendRequest',
            replica__service__pb2.ReplicaRequest.SerializeToString,
            replica__service__pb2.ReplicaReply.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)

    @staticmethod
    def Ping(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(
            request,
            target,
            '/protos.WorkerService/Ping',
            google_dot_protobuf_dot_empty__pb2.Empty.SerializeToString,
            common__pb2.Ack.FromString,
            options,
            channel_credentials,
            insecure,
            call_credentials,
            compression,
            wait_for_ready,
            timeout,
            metadata,
            _registered_method=True)
