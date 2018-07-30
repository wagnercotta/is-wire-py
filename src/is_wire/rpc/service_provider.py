from ..core import Channel, Subscription, Status, StatusCode, Logger
from ..core.utils import assert_type
from .context import Context
import traceback
import six
from google.protobuf.json_format import ParseError


class ServiceProvider(object):
    log = Logger("ServiceProvider", Logger.DEBUG)

    def __init__(self, channel):
        assert_type(channel, Channel, "channel")
        self._channel = channel
        self._services = {}
        self._interceptors_before = []
        self._interceptors_after = []

    def delegate(self, topic, function, request_type, reply_type):
        """ Bind a function to a particular topic, so everytime a message is
            received in this topic the function will be called """
        assert_type(topic, six.string_types, "topic")
        self.log.debug("New service registered '{}'", topic)
        subscription = Subscription(self._channel, name=topic)
        wrapped = self.wrap(function, request_type, reply_type)
        self._services[subscription.id] = wrapped

    def add_interceptor(self, interceptor):
        itype = type(interceptor)
        if not hasattr(itype, "before_call") and \
           not hasattr(itype, "after_call"):
            raise TypeError("Interceptors must implement the Interceptor"
                            "concept or derive from the Interceptor class")
        self._interceptors_before.append(interceptor.before_call)
        self._interceptors_after.append(interceptor.after_call)

    def serve(self, message):
        """ Attempts to serve message """
        if message.subscription_id in self._services:
            reply = self._services[message.subscription_id](message)
            if reply.has_topic():
                self._channel.publish(reply)
        else:
            self.log.debug("Ignoring request\n{}", message.short_string())

    def run(self):
        """ Blocks the current thread listening for requests """
        self.log.info("Listening for requests")
        while True:
            self.serve(self._channel.consume())

    def wrap(self, function, request_type, reply_type):
        def safe_call(*args):
            try:
                result = function(*args)
                assert_type(result, (Status, reply_type), "function result")
                return result
            except Exception:
                return Status(
                    code=StatusCode.INTERNAL_ERROR,
                    why="Service throwed exception:\n{}".format(
                        traceback.format_exc()),
                )

        def run_interceptors(interceptors, *args):
            for interceptor in interceptors:
                try:
                    interceptor(*args)
                except Exception:
                    trace = traceback.format_exc()
                    self.log.error("Interceptor throwed exception:\n{}", trace)

        def wrapper(request):
            reply = request.create_reply()
            context = Context(request, reply)

            run_interceptors(self._interceptors_before, context)
            try:
                arg = request.unpack(request_type)
                result = safe_call(arg, context)
                if isinstance(result, Status):
                    reply.status = result
                else:
                    reply.pack(result)
                    reply.status = Status(code=StatusCode.OK)
            except ParseError:
                why = "Expected request type '{}' but received something else"\
                    .format(request_type.DESCRIPTOR.full_name)
                reply.status = Status(StatusCode.FAILED_PRECONDITION, why)
            except Exception:
                trace = traceback.format_exc()
                self.log.error("Unexpected error\n{}", trace)
                reply.status = Status(StatusCode.INTERNAL_ERROR, trace)

            run_interceptors(self._interceptors_after, context)
            return reply

        return wrapper
