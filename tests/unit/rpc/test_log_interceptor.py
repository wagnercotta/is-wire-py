import pytest
from is_wire.core import Message, Status, StatusCode
from is_wire.rpc import LogInterceptor
from is_wire.rpc.context import Context


def test_log_interceptor_creation():
    interceptor = LogInterceptor()
    assert interceptor.log is not None


def test_log_interceptor_before_call():
    interceptor = LogInterceptor()
    context = Context(Message(), Message())

    interceptor.before_call(context)

    assert hasattr(interceptor, "begin")
    assert interceptor.begin > 0


def test_log_interceptor_after_call_ok(caplog):
    import logging

    caplog.set_level(logging.INFO)

    interceptor = LogInterceptor()
    request = Message()
    request.topic = "test.topic"
    reply = Message()
    reply.status = Status(code=StatusCode.OK)
    context = Context(request, reply)

    interceptor.before_call(context)
    interceptor.after_call(context)

    assert "OK" in caplog.text or "took" in caplog.text


def test_log_interceptor_after_call_error(caplog):
    import logging

    caplog.set_level(logging.ERROR)

    interceptor = LogInterceptor()
    request = Message()
    request.topic = "test.topic"
    reply = Message()
    reply.status = Status(code=StatusCode.INTERNAL_ERROR, why="error")
    context = Context(request, reply)

    interceptor.before_call(context)
    interceptor.after_call(context)

    assert "INTERNAL_ERROR" in caplog.text or "error" in caplog.text
