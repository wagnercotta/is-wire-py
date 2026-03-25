import pytest
from is_wire.core import Message, Status, StatusCode
from is_wire.rpc import MetricsInterceptor
from is_wire.rpc.context import Context

# Create a single instance for all tests to avoid duplicate metrics registration
_metrics_interceptor = None


@pytest.fixture(scope="module")
def metrics_interceptor():
    """Fixture that creates a single MetricsInterceptor to avoid duplicate registration."""
    global _metrics_interceptor
    if _metrics_interceptor is None:
        _metrics_interceptor = MetricsInterceptor()
    return _metrics_interceptor


def test_metrics_interceptor_creation(metrics_interceptor):
    assert metrics_interceptor.log is not None
    assert metrics_interceptor.duration is not None
    assert metrics_interceptor.count is not None


def test_metrics_interceptor_before_call(metrics_interceptor):
    context = Context(Message(), Message())

    metrics_interceptor.before_call(context)

    assert hasattr(metrics_interceptor, "begin")
    assert metrics_interceptor.begin > 0


def test_metrics_interceptor_after_call(metrics_interceptor):
    request = Message()
    request.topic = "test.metrics"
    reply = Message()
    reply.status = Status(code=StatusCode.OK)
    context = Context(request, reply)

    metrics_interceptor.before_call(context)
    metrics_interceptor.after_call(context)

    # Metrics should be recorded (no assertion on values, just no errors)
