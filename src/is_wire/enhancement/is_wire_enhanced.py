import inspect
import re
import socket
from collections.abc import Mapping
from typing import List, Optional, Union

from ..core import Channel, Message, Subscription
from ..rpc import ServiceProvider


class IsWireEnhanced:
    def __init__(self, user: str, password: str, host: str, port: int):
        def validade_uri(uri):
            pattern = re.compile(
                r"^amqp:\/\/"
                r"(?P<user>[^:@\/]+):"
                r"(?P<password>[^@\/]+)@"
                r"(?P<host>[a-zA-Z0-9.\-]+)"
                r":(?P<port>\d+)$"
            )
            match = pattern.match(uri)
            if not match:
                raise ValueError(
                    "Invalid AMQP URI format. Expected format: amqp://user:password@host:port"
                )
            return uri

        self.uri = validade_uri(f"amqp://{user}:{password}@{host}:{port}")
        self.channel = Channel(uri=self.uri)
        self.service_provider = ServiceProvider(self.channel)
        self.subscriptions = Subscription(self.channel)

    def create_rpc_service(self, *args, **kwargs):
        autorun = kwargs.pop("autorun", False)

        def extract_function_parameters(func):
            sig = inspect.signature(func)
            params = list(sig.parameters.values())

            if len(params) != 1:
                raise ValueError(
                    f"Function '{func.__name__}' must have exactly one parameter."
                )
            if sig.return_annotation is sig.empty:
                raise ValueError(
                    f"Function '{func.__name__}' must have a return type annotation."
                )
            if any(p.annotation is p.empty for p in params):
                raise ValueError(
                    f"Function '{func.__name__}' must have a type annotation for all parameters."
                )
            return params[0].annotation, sig.return_annotation

        def register(topic, func):
            request_type, reply_type = extract_function_parameters(func)

            def wrapped(request, context):
                sig = inspect.signature(func)
                if len(sig.parameters) == 1:
                    return func(request)
                elif len(sig.parameters) == 2:
                    return func(request, context)
                else:
                    raise ValueError(
                        f"Function '{func.__name__}' must accept 1 or 2 parameters (request[, context])."
                    )

            self.service_provider.delegate(
                topic=topic,
                function=wrapped,
                request_type=request_type,
                reply_type=reply_type,
            )

        if len(args) == 1 and isinstance(args[0], Mapping):
            mapping = args[0]
            for topic, func in mapping.items():
                register(topic, func)

        elif "topic" in kwargs and "function" in kwargs:
            register(kwargs["topic"], kwargs["function"])

        else:
            raise ValueError(
                "Invalid arguments. Use either:\n"
                " - create_rpc_service(topic='topic', function=func)\n"
                " - create_rpc_service({'topic': func, 'topic2': func2})"
            )
        if autorun:
            self.service_provider.run()

    def run(self):
        self.service_provider.run()

    def consume_message(
        self,
        amount: int,
        topic: str,
        timeout: Optional[int] = None,
    ):
        if amount is None:
            amount = 1

        self.subscriptions.subscribe(topic)
        consumed_messages: List[Message] = []

        while len(consumed_messages) < amount:
            try:
                msg = self.channel.consume(timeout=timeout)
                consumed_messages.append(msg)
            except socket.timeout:
                print("Timeout while waiting for messages.")
                consumed_messages.append(None)
        return consumed_messages if amount >= 2 else consumed_messages[0]

    def publish(self, topic: Union[str, List[str]], message: Message):
        if isinstance(topic, str):
            topic = [topic]
        for t in topic:
            self.channel.publish(topic=t, message=message)
