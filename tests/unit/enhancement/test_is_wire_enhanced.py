import pytest
from google.protobuf.wrappers_pb2 import Int64Value, StringValue
from is_wire.enhancement import IsWireEnhanced


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
