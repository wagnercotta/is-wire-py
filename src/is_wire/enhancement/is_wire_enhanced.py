import inspect
import re
import socket
from collections.abc import Mapping
from typing import Any, Callable, Optional, Tuple, Union

from ..core import Channel, Message, Subscription
from ..rpc import ServiceProvider


class IsWireEnhanced:
    _AMQP_URI_PATTERN = re.compile(
        r"^amqp:\/\/"
        r"(?P<user>[^:@\/]+):"
        r"(?P<password>[^@\/]+)@"
        r"(?P<host>[a-zA-Z0-9.\-]+)"
        r":(?P<port>\d+)$"
    )

    def __init__(self, user: str, password: str, host: str, port: int):
        self.uri = self._validate_uri(
            f"amqp://{user}:{password}@{host}:{port}"
        )
        self.channel = Channel(uri=self.uri)
        self.service_provider = ServiceProvider(self.channel)
        self.subscriptions = Subscription(self.channel)

    @classmethod
    def _validate_uri(cls, uri: str) -> str:
        if not cls._AMQP_URI_PATTERN.match(uri):
            raise ValueError(
                "Invalid AMQP URI format. Expected format: "
                "amqp://user:password@host:port"
            )
        return uri

    @staticmethod
    def _extract_function_parameters(
        func: Callable[..., Any],
    ) -> Tuple[Any, Any, int]:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if len(params) not in (1, 2):
            raise ValueError(
                f"Function '{func.__name__}' must accept 1 or 2 parameters "
                "(request[, context])."
            )
        if sig.return_annotation is sig.empty:
            raise ValueError(
                f"Function '{func.__name__}' must have a return type "
                "annotation."
            )
        if any(param.annotation is param.empty for param in params):
            raise ValueError(
                f"Function '{func.__name__}' must have a type annotation "
                "for all parameters."
            )
        return params[0].annotation, sig.return_annotation, len(params)

    def _register_rpc_service(
        self,
        topic: str,
        func: Callable[..., Any],
    ) -> None:
        request_type, reply_type, parameter_count = (
            self._extract_function_parameters(func)
        )

        def wrapped(request, context):
            if parameter_count == 1:
                return func(request)
            return func(request, context)

        self.service_provider.delegate(
            topic=topic,
            function=wrapped,
            request_type=request_type,
            reply_type=reply_type,
        )

    def create_rpc_service(self, *args, **kwargs) -> None:
        autorun = kwargs.pop("autorun", False)

        if len(args) == 1 and isinstance(args[0], Mapping):
            mapping = args[0]
            for topic, func in mapping.items():
                self._register_rpc_service(topic, func)

        elif "topic" in kwargs and "function" in kwargs:
            self._register_rpc_service(kwargs["topic"], kwargs["function"])

        else:
            raise ValueError(
                "Invalid arguments. Use either:\n"
                " - create_rpc_service(topic='topic', function=func)\n"
                " - create_rpc_service({'topic': func, 'topic2': func2})"
            )
        if autorun:
            self.service_provider.run()

    def run(self) -> None:
        self.service_provider.run()

    def consume_message(
        self,
        topic: str,
        amount: int = 1,
        timeout: Optional[float] = None,
    ) -> Union[Optional[Message], list[Optional[Message]]]:
        if amount < 1:
            raise ValueError("amount must be greater than or equal to 1.")

        self.subscriptions.subscribe(topic)
        consumed_messages = []

        while len(consumed_messages) < amount:
            try:
                msg = self.channel.consume(timeout=timeout)
                consumed_messages.append(msg)
            except socket.timeout:
                consumed_messages.append(None)
        return consumed_messages if amount >= 2 else consumed_messages[0]

    def publish(self, topic: Union[str, list[str]], message: Message) -> None:
        if isinstance(topic, str):
            topic = [topic]
        for t in topic:
            self.channel.publish(topic=t, message=message)
