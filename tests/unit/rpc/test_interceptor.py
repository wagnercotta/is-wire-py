from is_wire.rpc import Interceptor


def test_interceptor_default_before_call():
    interceptor = Interceptor()
    # Should not raise - it's a no-op
    result = interceptor.before_call(None)
    assert result is None


def test_interceptor_default_after_call():
    interceptor = Interceptor()
    # Should not raise - it's a no-op
    result = interceptor.after_call(None)
    assert result is None


def test_interceptor_subclass():
    class CustomInterceptor(Interceptor):
        def __init__(self):
            self.before_called = False
            self.after_called = False

        def before_call(self, context):
            self.before_called = True

        def after_call(self, context):
            self.after_called = True

    interceptor = CustomInterceptor()

    interceptor.before_call(None)
    assert interceptor.before_called is True

    interceptor.after_call(None)
    assert interceptor.after_called is True


def test_interceptor_can_store_state():
    class StatefulInterceptor(Interceptor):
        def __init__(self):
            self.start_time = None

        def before_call(self, context):
            self.start_time = 12345

        def after_call(self, context):
            return self.start_time

    interceptor = StatefulInterceptor()
    interceptor.before_call(None)
    result = interceptor.after_call(None)

    assert result == 12345
