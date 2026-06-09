import socket

import pytest
from google.protobuf.wrappers_pb2 import Int64Value, StringValue
from is_wire.core import Message
from is_wire.enhancement import IsWireEnhanced


class FakeChannel:
    def __init__(self, uri=None):
        self.uri = uri
        self.published = []
        self.closed = False

    def consume(self, timeout=None):
        raise socket.timeout

    def publish(self, topic, message):
        self.published.append((topic, message))

    def close(self):
        self.closed = True


class FakeSubscriptions:
    def __init__(self, channel=None):
        self.channel = channel
        self.topics = []

    def subscribe(self, topic):
        self.topics.append(topic)


class FakeServiceProvider:
    def __init__(self, channel=None):
        self.channel = channel
        self.delegated = None

    def delegate(self, **kwargs):
        self.delegated = kwargs


def make_wire():
    wire = IsWireEnhanced.__new__(IsWireEnhanced)
    wire._channel = FakeChannel()
    wire._subscription = FakeSubscriptions()
    wire._service_provider = FakeServiceProvider()
    wire._subscribed_topics = set()
    return wire


def test_constructor_accepts_factories_for_composition():
    wire = IsWireEnhanced(
        user="guest",
        password="guest",
        host="localhost",
        port=5672,
        channel_factory=FakeChannel,
        service_provider_factory=FakeServiceProvider,
        subscription_factory=FakeSubscriptions,
    )

    assert wire.uri == "amqp://guest:guest@localhost:5672"
    assert wire._channel.uri == wire.uri
    assert wire._service_provider.channel is wire._channel
    assert wire._subscription.channel is wire._channel


def test_invalid_uri_empty_user():
    with pytest.raises(ValueError, match="Invalid AMQP URI format"):
        IsWireEnhanced(
            user="",
            password="guest",
            host="localhost",
            port=5672,
        )


def test_invalid_uri_empty_password():
    with pytest.raises(ValueError, match="Invalid AMQP URI format"):
        IsWireEnhanced(
            user="guest",
            password="",
            host="localhost",
            port=5672,
        )


def test_invalid_uri_empty_host():
    with pytest.raises(ValueError, match="Invalid AMQP URI format"):
        IsWireEnhanced(
            user="guest",
            password="guest",
            host="",
            port=5672,
        )


def test_invalid_uri_empty_port():
    with pytest.raises(ValueError, match="Invalid AMQP URI format"):
        IsWireEnhanced(
            user="guest",
            password="guest",
            host="localhost",
            port=None,
        )


def test_consume_message_defaults_to_single_message_without_print(capsys):
    wire = make_wire()

    result = wire.consume_message("test.topic", timeout=0.1)

    assert result is None
    assert wire._subscription.topics == ["test.topic"]
    assert capsys.readouterr().out == ""


def test_consume_message_accepts_no_topic():
    wire = make_wire()

    result = wire.consume_message(timeout=0.1)

    assert result is None
    assert wire._subscription.topics == []


def test_consume_message_returns_list_for_multiple_messages():
    wire = make_wire()

    result = wire.consume_message("test.topic", amount=2, timeout=0.1)

    assert result == [None, None]
    assert wire._subscription.topics == ["test.topic"]


def test_consume_message_subscribes_only_once_per_topic():
    wire = make_wire()

    wire.consume_message("test.topic", timeout=0.1)
    wire.consume_message("test.topic", timeout=0.1)

    assert wire._subscription.topics == ["test.topic"]


def test_consume_message_rejects_non_positive_amount():
    wire = make_wire()

    with pytest.raises(ValueError, match="amount"):
        wire.consume_message("test.topic", amount=0)


def test_consume_message_rejects_invalid_timeout():
    wire = make_wire()

    with pytest.raises(ValueError, match="timeout"):
        wire.consume_message("test.topic", timeout=-1)


def test_consume_message_requires_timeout_for_multiple_messages():
    wire = make_wire()

    with pytest.raises(ValueError, match="timeout"):
        wire.consume_message("test.topic", amount=2)


def test_consume_message_rejects_invalid_topic():
    wire = make_wire()

    with pytest.raises(ValueError, match="topic"):
        wire.consume_message("", timeout=0.1)


def test_rpc_service_accepts_request_and_context_parameters():
    wire = make_wire()

    def service(request: Int64Value, context: object) -> StringValue:
        return StringValue(value=str(request.value))

    wire.create_rpc_service(topic="topic", function=service)

    delegated = wire._service_provider.delegated
    assert delegated["topic"] == "topic"
    assert delegated["request_type"] is Int64Value
    assert delegated["reply_type"] is StringValue
    assert delegated["function"](Int64Value(value=7), object()).value == "7"


def test_rpc_service_accepts_callable_objects():
    wire = make_wire()

    class Service:
        def __call__(self, request: Int64Value) -> StringValue:
            return StringValue(value=str(request.value))

    wire.create_rpc_service(topic="topic", function=Service())

    delegated = wire._service_provider.delegated
    assert delegated["request_type"] is Int64Value
    assert delegated["reply_type"] is StringValue
    assert delegated["function"](Int64Value(value=9), object()).value == "9"


def test_create_rpc_service_rejects_extra_arguments():
    wire = make_wire()

    def service(request: Int64Value) -> StringValue:
        return StringValue(value=str(request.value))

    with pytest.raises(ValueError, match="Invalid arguments"):
        wire.create_rpc_service({"topic": service}, topic="other")


def test_create_rpc_service_rejects_non_callable_function():
    wire = make_wire()

    with pytest.raises(ValueError, match="callable"):
        wire.create_rpc_service(topic="topic", function=object())


def test_publish_accepts_single_and_multiple_topics():
    wire = make_wire()
    message = Message()
    message.body = b"payload"

    wire.publish("topic.one", message)
    wire.publish(["topic.two", "topic.three"], message)

    assert wire._channel.published == [
        ("topic.one", message),
        ("topic.two", message),
        ("topic.three", message),
    ]


def test_publish_rejects_invalid_topic_or_message():
    wire = make_wire()
    message = Message()

    with pytest.raises(ValueError, match="topic"):
        wire.publish([], message)
    with pytest.raises(ValueError, match="message"):
        wire.publish("topic", object())


def test_context_manager_closes_channel():
    wire = make_wire()

    with wire as same_wire:
        assert same_wire is wire

    assert wire._channel.closed is True
