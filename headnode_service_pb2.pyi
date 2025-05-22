from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ReplicaCreationRequest(_message.Message):
    __slots__ = ("base_node_address", "num_resources", "resource_name")
    BASE_NODE_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    NUM_RESOURCES_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_NAME_FIELD_NUMBER: _ClassVar[int]
    base_node_address: str
    num_resources: int
    resource_name: str
    def __init__(self, base_node_address: _Optional[str] = ..., num_resources: _Optional[int] = ..., resource_name: _Optional[str] = ...) -> None: ...

class ReplicaCreationReply(_message.Message):
    __slots__ = ("worker_id", "replica_id", "created")
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    REPLICA_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_FIELD_NUMBER: _ClassVar[int]
    worker_id: int
    replica_id: int
    created: bool
    def __init__(self, worker_id: _Optional[int] = ..., replica_id: _Optional[int] = ..., created: bool = ...) -> None: ...

class Message(_message.Message):
    __slots__ = ("model", "input")
    MODEL_FIELD_NUMBER: _ClassVar[int]
    INPUT_FIELD_NUMBER: _ClassVar[int]
    model: str
    input: str
    def __init__(self, model: _Optional[str] = ..., input: _Optional[str] = ...) -> None: ...

class ReplicaRequest(_message.Message):
    __slots__ = ("worker_id", "replica_id", "message")
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    REPLICA_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    worker_id: int
    replica_id: int
    message: Message
    def __init__(self, worker_id: _Optional[int] = ..., replica_id: _Optional[int] = ..., message: _Optional[_Union[Message, _Mapping]] = ...) -> None: ...

class ReplicaReply(_message.Message):
    __slots__ = ("worker_id", "replica_id", "output")
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    REPLICA_ID_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_FIELD_NUMBER: _ClassVar[int]
    worker_id: int
    replica_id: int
    output: str
    def __init__(self, worker_id: _Optional[int] = ..., replica_id: _Optional[int] = ..., output: _Optional[str] = ...) -> None: ...

class Resource(_message.Message):
    __slots__ = ("used_resources", "name", "state", "queue_length")
    USED_RESOURCES_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    QUEUE_LENGTH_FIELD_NUMBER: _ClassVar[int]
    used_resources: int
    name: str
    state: str
    queue_length: int
    def __init__(self, used_resources: _Optional[int] = ..., name: _Optional[str] = ..., state: _Optional[str] = ..., queue_length: _Optional[int] = ...) -> None: ...

class ReplicaState(_message.Message):
    __slots__ = ("replica_id", "queue_size", "status")
    REPLICA_ID_FIELD_NUMBER: _ClassVar[int]
    QUEUE_SIZE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    replica_id: int
    queue_size: int
    status: str
    def __init__(self, replica_id: _Optional[int] = ..., queue_size: _Optional[int] = ..., status: _Optional[str] = ...) -> None: ...

class HealthStatusUpdate(_message.Message):
    __slots__ = ("worker_id", "state", "replica_states")
    WORKER_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    REPLICA_STATES_FIELD_NUMBER: _ClassVar[int]
    worker_id: int
    state: str
    replica_states: _containers.RepeatedCompositeFieldContainer[ReplicaState]
    def __init__(self, worker_id: _Optional[int] = ..., state: _Optional[str] = ..., replica_states: _Optional[_Iterable[_Union[ReplicaState, _Mapping]]] = ...) -> None: ...

class HealthStatusReply(_message.Message):
    __slots__ = ("ack", "isAlive")
    ACK_FIELD_NUMBER: _ClassVar[int]
    ISALIVE_FIELD_NUMBER: _ClassVar[int]
    ack: bool
    isAlive: str
    def __init__(self, ack: bool = ..., isAlive: _Optional[str] = ...) -> None: ...

class RegisterRequest(_message.Message):
    __slots__ = ("node_id", "node_address", "port", "state")
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    PORT_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    node_id: int
    node_address: str
    port: str
    state: str
    def __init__(self, node_id: _Optional[int] = ..., node_address: _Optional[str] = ..., port: _Optional[str] = ..., state: _Optional[str] = ...) -> None: ...

class RegisterReply(_message.Message):
    __slots__ = ("ack",)
    ACK_FIELD_NUMBER: _ClassVar[int]
    ack: bool
    def __init__(self, ack: bool = ...) -> None: ...
