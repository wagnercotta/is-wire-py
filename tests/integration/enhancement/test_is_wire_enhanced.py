import asyncio
import socket

import pytest
from google.protobuf.wrappers_pb2 import Int64Value, StringValue
from is_wire.core import Message

pytestmark = pytest.mark.integration


def test_valid_uri_construction(enhanced):
    assert enhanced.uri == "amqp://guest:guest@localhost:5672"


def test_create_rpc_service_with_dict(enhanced):
    def my_service(request: Int64Value) -> StringValue:
        return StringValue(value=str(request.value))

    enhanced.create_rpc_service({"Enhanced.Service": my_service})


def test_create_rpc_service_with_kwargs(enhanced):
    def my_service(request: Int64Value) -> StringValue:
        return StringValue(value=str(request.value))

    enhanced.create_rpc_service(topic="Enhanced.Kwargs", function=my_service)


def test_create_rpc_service_invalid_args(enhanced):
    with pytest.raises(ValueError, match="Invalid arguments"):
        enhanced.create_rpc_service()


def test_create_rpc_service_missing_return_annotation(enhanced):
    def bad_service(request: Int64Value):
        pass

    with pytest.raises(ValueError, match="return type annotation"):
        enhanced.create_rpc_service({"topic": bad_service})


def test_create_rpc_service_missing_param_annotation(enhanced):
    def bad_service(request) -> StringValue:
        return StringValue()

    with pytest.raises(ValueError, match="type annotation"):
        enhanced.create_rpc_service({"topic": bad_service})


def test_create_rpc_service_wrong_param_count(enhanced):
    def bad_service(a: Int64Value, b: Int64Value) -> StringValue:
        return StringValue()

    with pytest.raises(ValueError, match="exactly one parameter"):
        enhanced.create_rpc_service({"topic": bad_service})


def test_create_rpc_service_multiple_topics(enhanced):
    def service1(request: Int64Value) -> StringValue:
        return StringValue()

    def service2(request: StringValue) -> Int64Value:
        return Int64Value()

    enhanced.create_rpc_service(
        {"Enhanced.Topic1": service1, "Enhanced.Topic2": service2}
    )


@pytest.mark.asyncio
async def test_publish_single_topic(enhanced, topic):
    enhanced.subscriptions.subscribe(topic)

    msg = Message()
    msg.body = b"test message"

    enhanced.publish(topic, msg)

    received = await asyncio.to_thread(enhanced.channel.consume, timeout=1.0)

    assert received.body == b"test message"


@pytest.mark.asyncio
async def test_publish_multiple_topics(enhanced):
    topics = ["test.multi.1", "test.multi.2", "test.multi.3"]

    for t in topics:
        enhanced.subscriptions.subscribe(t)

    msg = Message()
    msg.body = b"multi topic"
    enhanced.publish(topics, msg)

    received = []
    for _ in range(3):
        try:
            m = await asyncio.to_thread(enhanced.channel.consume, timeout=1.0)
            received.append(m)
        except socket.timeout:
            break

    assert len(received) == 3


@pytest.mark.asyncio
async def test_consume_single_message(enhanced, topic):
    enhanced.subscriptions.subscribe(topic)

    msg = Message()
    msg.body = b"consume test"
    enhanced.channel.publish(msg, topic=topic)

    received = await asyncio.to_thread(enhanced.channel.consume, timeout=1.0)

    assert received is not None
    assert received.body == b"consume test"


@pytest.mark.asyncio
async def test_consume_message_timeout(enhanced):
    result = await asyncio.to_thread(
        enhanced.consume_message,
        topic="Enhanced.NoMessages.Test",
        timeout=0.5,
        amount=1,
    )

    assert result is None


@pytest.mark.asyncio
async def test_consume_multiple_messages(enhanced, topic):
    # Subscribe before publish
    enhanced.subscriptions.subscribe(topic)

    for i in range(3):
        msg = Message()
        msg.body = f"message {i}".encode("latin")
        enhanced.channel.publish(msg, topic=topic)

    messages = []
    for _ in range(3):
        try:
            m = await asyncio.to_thread(enhanced.channel.consume, timeout=1.0)
            messages.append(m)
        except socket.timeout:
            break

    assert len(messages) == 3
    assert all(m is not None for m in messages)
