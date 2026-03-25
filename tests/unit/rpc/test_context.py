import pytest
from is_wire.core import Message
from is_wire.rpc.context import Context


def test_context_creation():
    request = Message()
    reply = Message()
    context = Context(request, reply)

    assert context.request is request
    assert context.reply is reply


def test_context_request_property():
    request = Message()
    request.topic = "test.topic"
    reply = Message()

    context = Context(request, reply)

    assert context.request.topic == "test.topic"


def test_context_reply_property():
    request = Message()
    reply = Message()
    reply.topic = "reply.topic"

    context = Context(request, reply)

    assert context.reply.topic == "reply.topic"


def test_context_addons_empty():
    context = Context(Message(), Message())
    assert context.addons == {}


def test_context_addons_storage():
    context = Context(Message(), Message())

    context.addons["key1"] = "value1"
    context.addons["key2"] = {"nested": True}

    assert context.addons["key1"] == "value1"
    assert context.addons["key2"]["nested"] is True


def test_context_addons_persistence():
    context = Context(Message(), Message())
    context.addons["data"] = [1, 2, 3]

    # Addons should persist across accesses
    assert context.addons["data"] == [1, 2, 3]
    context.addons["data"].append(4)
    assert context.addons["data"] == [1, 2, 3, 4]
