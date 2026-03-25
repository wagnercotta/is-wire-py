import pytest
from google.protobuf.struct_pb2 import Struct
from google.protobuf.wrappers_pb2 import Int64Value
from is_wire.core import Message, Status, StatusCode, Subscription
from is_wire.rpc import Interceptor, LogInterceptor, ServiceProvider

pytestmark = pytest.mark.integration


def my_service(request, context):
    value = int(request.fields["value"].number_value)
    return Int64Value(value=value)


def test_rpc(channel):
    service = ServiceProvider(channel)
    service.delegate("MyService", my_service, Struct, Int64Value)

    subscription = Subscription(channel)

    struct = Struct()
    struct.fields["value"].number_value = 42
    message = Message(struct)
    message.reply_to = subscription

    channel.publish(topic="MyService", message=message)

    request = channel.consume(timeout=1.0)
    service.serve(request)

    reply = channel.consume(timeout=1.0)
    result = reply.unpack(Int64Value)

    assert result.value == 42


def test_delegate_duplicate(channel):
    service = ServiceProvider(channel)
    service.delegate("DuplicateService", lambda r, c: None, object, object)

    with pytest.raises(RuntimeError, match="already delegated"):
        service.delegate("DuplicateService", lambda r, c: None, object, object)


def test_should_serve(channel):
    service = ServiceProvider(channel)
    service.delegate("ShouldServe", my_service, Struct, Int64Value)

    subscription = Subscription(channel)
    struct = Struct()
    message = Message(struct)
    message.reply_to = subscription

    channel.publish(topic="ShouldServe", message=message)
    request = channel.consume(timeout=1.0)

    assert service.should_serve(request) is True


def test_should_not_serve_unknown(channel):
    service = ServiceProvider(channel)
    message = Message()
    message.subscription_id = "unknown_id"

    assert service.should_serve(message) is False


def test_serve_unknown_raises(channel):
    service = ServiceProvider(channel)
    message = Message()
    message.subscription_id = "unknown_id"

    with pytest.raises(RuntimeError, match="Cannot serve message"):
        service.serve(message)


def test_add_interceptor(channel):
    service = ServiceProvider(channel)

    class CustomInterceptor(Interceptor):
        def __init__(self):
            self.before_called = False
            self.after_called = False

        def before_call(self, context):
            self.before_called = True

        def after_call(self, context):
            self.after_called = True

    interceptor = CustomInterceptor()
    service.add_interceptor(interceptor)

    service.delegate("InterceptorService", my_service, Struct, Int64Value)

    subscription = Subscription(channel)
    struct = Struct()
    struct.fields["value"].number_value = 10
    message = Message(struct)
    message.reply_to = subscription

    channel.publish(topic="InterceptorService", message=message)
    request = channel.consume(timeout=1.0)
    service.serve(request)

    assert interceptor.before_called is True
    assert interceptor.after_called is True


def test_add_invalid_interceptor(channel):
    service = ServiceProvider(channel)

    class NotAnInterceptor:
        pass

    with pytest.raises(TypeError, match="Interceptor"):
        service.add_interceptor(NotAnInterceptor())


def test_service_returns_status(channel):
    def status_service(request, context):
        return Status(code=StatusCode.NOT_FOUND, why="item not found")

    service = ServiceProvider(channel)
    service.delegate("StatusService", status_service, Struct, Int64Value)

    subscription = Subscription(channel)
    message = Message(Struct())
    message.reply_to = subscription

    channel.publish(topic="StatusService", message=message)
    request = channel.consume(timeout=1.0)
    service.serve(request)

    reply = channel.consume(timeout=1.0)
    assert reply.status.code == StatusCode.NOT_FOUND


def test_service_with_log_interceptor(channel):
    service = ServiceProvider(channel)
    service.add_interceptor(LogInterceptor())
    service.delegate("LogService", my_service, Struct, Int64Value)

    subscription = Subscription(channel)
    struct = Struct()
    struct.fields["value"].number_value = 5
    message = Message(struct)
    message.reply_to = subscription

    channel.publish(topic="LogService", message=message)
    request = channel.consume(timeout=1.0)
    service.serve(request)

    reply = channel.consume(timeout=1.0)
    result = reply.unpack(Int64Value)
    assert result.value == 5
