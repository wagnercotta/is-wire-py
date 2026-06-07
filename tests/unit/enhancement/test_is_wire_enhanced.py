import socket

import pytest
from google.protobuf.wrappers_pb2 import Int64Value, StringValue
from is_wire.enhancement import IsWireEnhanced


class FakeChannel:
    def consume(self, timeout=None):
        raise socket.timeout


class FakeSubscriptions:
    def __init__(self):
        self.topics = []

    def subscribe(self, topic):
        self.topics.append(topic)


class FakeServiceProvider:
    def __init__(self):
        self.delegated = None

    def delegate(self, **kwargs):
        self.delegated = kwargs


def make_wire():
    wire = IsWireEnhanced.__new__(IsWireEnhanced)
    wire.channel = FakeChannel()
    wire.subscriptions = FakeSubscriptions()
    wire.service_provider = FakeServiceProvider()
    return wire


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
    assert wire.subscriptions.topics == ["test.topic"]
    assert capsys.readouterr().out == ""


def test_consume_message_returns_list_for_multiple_messages():
    wire = make_wire()

    result = wire.consume_message("test.topic", amount=2, timeout=0.1)

    assert result == [None, None]
    assert wire.subscriptions.topics == ["test.topic"]


def test_consume_message_rejects_non_positive_amount():
    wire = make_wire()

    with pytest.raises(ValueError, match="amount"):
        wire.consume_message("test.topic", amount=0)


def test_rpc_service_accepts_request_and_context_parameters():
    wire = make_wire()

    def service(request: Int64Value, context: object) -> StringValue:
        return StringValue(value=str(request.value))

    wire.create_rpc_service(topic="topic", function=service)

    delegated = wire.service_provider.delegated
    assert delegated["topic"] == "topic"
    assert delegated["request_type"] is Int64Value
    assert delegated["reply_type"] is StringValue
    assert delegated["function"](Int64Value(value=7), object()).value == "7"
