import pytest
from google.protobuf.struct_pb2 import Struct
from is_wire.core import ContentType, Message, Status, StatusCode


def test_default_constructor():
    message = Message()
    assert message.has_body() is False
    assert message.has_topic() is False
    assert message.has_created_at() is True
    assert message.has_content_type() is False
    assert message.has_correlation_id() is False
    assert message.has_reply_to() is False
    assert message.has_subscription_id() is False
    assert message.has_timeout() is False
    assert message.has_metadata() is False
    assert message.has_status() is False


def test_constructor_with_bytes_content():
    message = Message(content=b"test bytes")
    assert message.body == b"test bytes"


def test_constructor_with_protobuf_content():
    struct = Struct()
    struct.fields["key"].string_value = "value"
    message = Message(content=struct)
    assert message.has_body()
    assert message.content_type == ContentType.PROTOBUF


def test_constructor_with_content_type():
    message = Message(content_type=ContentType.JSON)
    assert message.content_type == ContentType.JSON


@pytest.mark.parametrize(
    "attr,value",
    [
        ("topic", "string"),
        ("reply_to", "string"),
        ("subscription_id", "string"),
        ("correlation_id", -1),
        ("body", b"bytes"),
    ],
)
def test_has_field(attr, value):
    message = Message()
    setattr(message, attr, value)
    assert getattr(message, attr) == value


def test_topic_property():
    message = Message()
    assert message.topic is None
    message.topic = "my.topic"
    assert message.topic == "my.topic"
    assert message.has_topic() is True


def test_topic_invalid_type():
    message = Message()
    with pytest.raises(TypeError, match="topic"):
        message.topic = 123


def test_body_property():
    message = Message()
    message.body = b"test body"
    assert message.body == b"test body"
    assert message.has_body() is True


def test_body_invalid_type():
    message = Message()
    with pytest.raises(TypeError, match="body"):
        message.body = "not bytes"


def test_correlation_id_property():
    message = Message()
    message.correlation_id = 12345
    assert message.correlation_id == 12345
    assert message.has_correlation_id() is True


def test_correlation_id_invalid_type():
    message = Message()
    with pytest.raises(TypeError, match="correlation_id"):
        message.correlation_id = "not int"


def test_timeout_property():
    message = Message()
    message.timeout = 5.0
    assert message.timeout == 5.0
    assert message.has_timeout() is True


def test_timeout_accepts_int():
    message = Message()
    message.timeout = 5
    assert message.timeout == 5


def test_timeout_invalid_type():
    message = Message()
    with pytest.raises(TypeError, match="timeout"):
        message.timeout = "invalid"


def test_metadata_property():
    message = Message()
    message.metadata = {"key": "value"}
    assert message.metadata == {"key": "value"}
    assert message.has_metadata() is True


def test_metadata_empty():
    message = Message()
    assert message.has_metadata() is False
    message.metadata = {}
    assert message.has_metadata() is False


def test_metadata_invalid_type():
    message = Message()
    with pytest.raises(TypeError, match="metadata"):
        message.metadata = "not dict"


def test_status_property():
    message = Message()
    status = Status(code=StatusCode.OK)
    message.status = status
    assert message.status == status
    assert message.has_status() is True


def test_status_invalid_type():
    message = Message()
    with pytest.raises(TypeError, match="status"):
        message.status = "not status"


def test_content_type_property():
    message = Message()
    message.content_type = ContentType.JSON
    assert message.content_type == ContentType.JSON
    assert message.has_content_type() is True


def test_content_type_invalid_type():
    message = Message()
    with pytest.raises(TypeError, match="content_type"):
        message.content_type = "application/json"


def test_created_at_property():
    message = Message()
    assert message.has_created_at() is True
    message.created_at = 1000.0
    assert message.created_at == 1000.0


def test_deadline_exceeded_no_timeout():
    message = Message()
    assert message.deadline_exceeded() is False


def test_deadline_exceeded_false():
    message = Message()
    message.timeout = 1000.0  # far in future
    assert message.deadline_exceeded() is False


def test_deadline_exceeded_true():
    message = Message()
    message.created_at = 0  # epoch
    message.timeout = 1.0  # 1 second after epoch
    assert message.deadline_exceeded() is True


def test_pack_unpack_protobuf():
    struct = Struct()
    struct.fields["value"].number_value = 90.0

    message = Message()
    message.pack(struct)
    unpacked = message.unpack(Struct)

    assert struct == unpacked
    assert message.content_type == ContentType.PROTOBUF


def test_pack_unpack_json():
    struct = Struct()
    struct.fields["name"].string_value = "test"

    message = Message()
    message.content_type = ContentType.JSON
    message.pack(struct)
    unpacked = message.unpack(Struct)

    assert (
        struct.fields["name"].string_value
        == unpacked.fields["name"].string_value
    )


def test_pack_dict():
    data = {"key": "value", "number": 42}
    message = Message()
    message.pack(data)
    assert message.content_type == ContentType.JSON


def test_unpack_dict():
    data = {"key": "value"}
    message = Message()
    message.pack(data)
    unpacked = message.unpack(dict)
    assert unpacked["key"] == "value"


def test_create_reply():
    request = Message()
    request.topic = "topic"
    request.reply_to = "reply_to"

    reply = request.create_reply()

    assert reply.topic == request.reply_to
    assert reply.correlation_id == request.correlation_id


def test_create_reply_preserves_content_type():
    request = Message()
    request.content_type = ContentType.JSON
    request.reply_to = "reply"

    reply = request.create_reply()

    assert reply.content_type == ContentType.JSON


def test_message_equality():
    m1 = Message()
    m1.topic = "topic"
    m1.body = b"body"

    m2 = Message()
    m2.topic = "topic"
    m2.body = b"body"
    m2._created_at = m1._created_at

    assert m1 == m2


def test_message_inequality():
    m1 = Message()
    m1.topic = "topic1"

    m2 = Message()
    m2.topic = "topic2"

    assert m1 != m2


def test_message_str():
    message = Message()
    message.topic = "test.topic"
    message.body = b"test"

    result = str(message)

    assert "test.topic" in result
    assert "body" in result


def test_message_short_string():
    message = Message()
    message.topic = "test.topic"
    message.body = b"test"

    result = message.short_string()

    assert "test.topic" in result
    assert "body" in result
