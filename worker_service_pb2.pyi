from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class TaskRequest(_message.Message):
    __slots__ = ("model", "input")
    MODEL_FIELD_NUMBER: _ClassVar[int]
    INPUT_FIELD_NUMBER: _ClassVar[int]
    model: str
    input: str
    def __init__(self, model: _Optional[str] = ..., input: _Optional[str] = ...) -> None: ...

class TaskReply(_message.Message):
    __slots__ = ("result",)
    RESULT_FIELD_NUMBER: _ClassVar[int]
    result: str
    def __init__(self, result: _Optional[str] = ...) -> None: ...

class HealthStatus(_message.Message):
    __slots__ = ("status", "replica_id")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    REPLICA_ID_FIELD_NUMBER: _ClassVar[int]
    status: str
    replica_id: int
    def __init__(self, status: _Optional[str] = ..., replica_id: _Optional[int] = ...) -> None: ...

class HealthReply(_message.Message):
    __slots__ = ("ack",)
    ACK_FIELD_NUMBER: _ClassVar[int]
    ack: bool
    def __init__(self, ack: bool = ...) -> None: ...

class Ack(_message.Message):
    __slots__ = ("acknowledged",)
    ACKNOWLEDGED_FIELD_NUMBER: _ClassVar[int]
    acknowledged: bool
    def __init__(self, acknowledged: bool = ...) -> None: ...

class replicaStatus(_message.Message):
    __slots__ = ("state", "replica_id", "pid", "port")
    STATE_FIELD_NUMBER: _ClassVar[int]
    REPLICA_ID_FIELD_NUMBER: _ClassVar[int]
    PID_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    state: str
    replica_id: int
    pid: int
    port: str
    def __init__(self, state: _Optional[str] = ..., replica_id: _Optional[int] = ..., pid: _Optional[int] = ..., port: _Optional[str] = ...) -> None: ...

class Reply(_message.Message):
    __slots__ = ("ack",)
    ACK_FIELD_NUMBER: _ClassVar[int]
    ack: bool
    def __init__(self, ack: bool = ...) -> None: ...
