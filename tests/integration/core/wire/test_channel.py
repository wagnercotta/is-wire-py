import socket

import pytest
from google.protobuf.struct_pb2 import Struct
from is_wire.core import Message, Subscription, now

pytestmark = pytest.mark.integration


def test_channel_publish_consume(channel):
    subscription = Subscription(channel)
    subscription.subscribe("MyTopic.Sub.Sub")

    struct = Struct()
    struct.fields["value"].number_value = 666.0

    sent = Message(struct)
    sent.reply_to = subscription
    sent.created_at = int(1000 * now()) / 1000.0
    sent.timeout = 1.0
    sent.topic = "MyTopic.Sub.Sub"

    channel.publish(message=sent)
    received = channel.consume(timeout=1.0)

    assert sent.body == received.body
    assert sent.topic == received.topic


def test_channel_full_message_roundtrip(channel):
    subscription = Subscription(channel)
    subscription.subscribe("Roundtrip.Test")

    struct = Struct()
    struct.fields["value"].number_value = 42.0

    sent = Message(struct)
    sent.reply_to = subscription
    sent.created_at = int(1000 * now()) / 1000.0
    sent.timeout = 2.0
    sent.topic = "Roundtrip.Test"
    sent.metadata = {"key": "value"}

    channel.publish(message=sent)
    received = channel.consume(timeout=1.0)

    assert sent.reply_to == received.reply_to
    assert sent.subscription_id == received.subscription_id
    assert sent.content_type == received.content_type
    assert sent.body == received.body
    assert sent.topic == received.topic
    assert sent.correlation_id == received.correlation_id
    assert sent.timeout == received.timeout
    assert sent.metadata == received.metadata
    assert sent.created_at == received.created_at


@pytest.mark.parametrize("size", [0, 1e4])
def test_body_sizes(channel, size):
    subscription = Subscription(channel)
    subscription.subscribe("Body.Size.Test")

    sent = Message()
    sent.reply_to = subscription
    sent.topic = "Body.Size.Test"
    sent.body = bytes(bytearray(range(256)) * int(size))

    channel.publish(message=sent)
    received = channel.consume(timeout=1.0)

    assert sent.body == received.body


def test_negative_timeout_raises(channel):
    with pytest.raises(AssertionError):
        channel.consume(timeout=-1e-10)


def test_zero_timeout_raises_socket_timeout(channel):
    with pytest.raises(socket.timeout):
        channel.consume(timeout=0)


def test_empty_topic_raises(channel):
    message = Message(content=b"body")

    with pytest.raises(RuntimeError):
        channel.publish(message)

    with pytest.raises(RuntimeError):
        channel.publish(message, topic="")


def test_publish_with_topic_arg(channel):
    subscription = Subscription(channel)
    message = Message(content=b"test body")

    channel.publish(message, topic=subscription.name)
    recv = channel.consume(timeout=1.0)

    assert recv.body == message.body


def test_publish_with_message_topic(channel):
    subscription = Subscription(channel)
    message = Message(content=b"test body")
    message.topic = subscription.name

    channel.publish(message)
    recv = channel.consume(timeout=1.0)

    assert recv.body == message.body


def test_multi_subscription(channel):
    subscription1 = Subscription(channel)
    subscription2 = Subscription(channel)
    message = Message()

    channel.publish(message, topic=subscription1.name)
    recv = channel.consume(timeout=1.0)
    assert recv.subscription_id == subscription1.name

    channel.publish(message, topic=subscription2.name)
    recv = channel.consume(timeout=1.0)
    assert recv.subscription_id == subscription2.name


def test_subscription_subscribe_unsubscribe(channel):
    subscription = Subscription(channel)
    topic = "Subscribe.Unsubscribe.Test"

    subscription.subscribe(topic)
    assert topic in subscription.topics

    message = Message()
    message.body = b"test"
    channel.publish(message, topic=topic)
    recv = channel.consume(timeout=1.0)
    assert recv.body == b"test"

    subscription.unsubscribe(topic)
    assert topic not in subscription.topics


def test_subscription_properties(channel):
    subscription = Subscription(channel)

    assert subscription.id is not None
    assert subscription.name is not None
    assert isinstance(subscription.topics, set)
