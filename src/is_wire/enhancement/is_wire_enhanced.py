import inspect
import re
import socket
from collections.abc import Mapping
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Union, get_type_hints

from ..core import Channel, Message, Subscription
from ..rpc import ServiceProvider


@dataclass(frozen=True)
class _RpcServiceDefinition:
    topic: str
    function: Callable[..., Any]
    request_type: Any
    reply_type: Any
    parameter_count: int


class IsWireEnhanced:
    _AMQP_URI_PATTERN = re.compile(
        r"^amqp:\/\/"
        r"(?P<user>[^:@\/]+):"
        r"(?P<password>[^@\/]+)@"
        r"(?P<host>[a-zA-Z0-9.\-]+)"
        r":(?P<port>\d+)$"
    )

    def __init__(
        self,
        user: str,
        password: str,
        host: str,
        port: int,
        *,
        channel_factory: Callable[[str], Channel] = Channel,
        service_provider_factory: Callable[[Channel], ServiceProvider] = (
            ServiceProvider
        ),
        subscription_factory: Callable[[Channel], Subscription] = (
            Subscription
        ),
    ):
        self.uri = self._build_uri(
            user=user,
            password=password,
            host=host,
            port=port,
        )
        self._channel = channel_factory(self.uri)
        self._service_provider = service_provider_factory(self._channel)
        self._subscription = subscription_factory(self._channel)
        self._subscribed_topics = set()

    @classmethod
    def _build_uri(
        cls,
        user: str,
        password: str,
        host: str,
        port: int,
    ) -> str:
        uri = f"amqp://{user}:{password}@{host}:{port}"
        return cls._validate_uri(uri)

    @classmethod
    def _validate_uri(cls, uri: str) -> str:
        if not cls._AMQP_URI_PATTERN.match(uri):
            raise ValueError(
                "Invalid AMQP URI format. Expected format: "
                "amqp://user:password@host:port"
            )
        return uri

    @staticmethod
    def _validate_topic(topic: str) -> str:
        if not isinstance(topic, str) or not topic:
            raise ValueError("topic must be a non-empty string.")
        return topic

    @classmethod
    def _normalize_topics(cls, topic: Union[str, list[str]]) -> list[str]:
        if isinstance(topic, str):
            return [cls._validate_topic(topic)]
        if not isinstance(topic, list) or not topic:
            raise ValueError("topic must be a non-empty string or list.")
        return [cls._validate_topic(item) for item in topic]

    def _subscribe_once(self, topic: str) -> None:
        topic = self._validate_topic(topic)
        subscribed_topics = getattr(self, "_subscribed_topics", None)
        if subscribed_topics is None:
            subscribed_topics = set()
            self._subscribed_topics = subscribed_topics
        if topic not in subscribed_topics:
            self._subscription.subscribe(topic)
            subscribed_topics.add(topic)

    @staticmethod
    def _extract_function_parameters(
        func: Callable[..., Any],
    ) -> Tuple[Any, Any, int]:
        if not callable(func):
            raise ValueError("function must be callable.")

        function_name = getattr(func, "__name__", func.__class__.__name__)
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if len(params) not in (1, 2):
            raise ValueError(
                f"Function '{function_name}' must accept 1 or 2 parameters "
                "(request[, context])."
            )
        if sig.return_annotation is sig.empty:
            raise ValueError(
                f"Function '{function_name}' must have a return type "
                "annotation."
            )
        if any(param.annotation is param.empty for param in params):
            raise ValueError(
                f"Function '{function_name}' must have a type annotation "
                "for all parameters."
            )

        hints_source = (
            func
            if inspect.isfunction(func) or inspect.ismethod(func)
            else getattr(func, "__call__", func)
        )
        try:
            type_hints = get_type_hints(hints_source)
        except Exception as exc:
            raise ValueError(
                f"Function '{function_name}' has invalid type annotations."
            ) from exc
        request_type = type_hints.get(params[0].name, params[0].annotation)
        reply_type = type_hints.get("return", sig.return_annotation)
        return request_type, reply_type, len(params)

    def _create_rpc_definition(
        self,
        topic: str,
        func: Callable[..., Any],
    ) -> _RpcServiceDefinition:
        request_type, reply_type, parameter_count = (
            self._extract_function_parameters(func)
        )
        return _RpcServiceDefinition(
            topic=self._validate_topic(topic),
            function=func,
            request_type=request_type,
            reply_type=reply_type,
            parameter_count=parameter_count,
        )

    def _register_rpc_service(
        self,
        topic: str,
        func: Callable[..., Any],
    ) -> None:
        service = self._create_rpc_definition(
            topic=topic,
            func=func,
        )

        @wraps(service.function)
        def wrapped(request, context):
            if service.parameter_count == 1:
                return service.function(request)
            return service.function(request, context)

        self._service_provider.delegate(
            topic=service.topic,
            function=wrapped,
            request_type=service.request_type,
            reply_type=service.reply_type,
        )

    def create_rpc_service(self, *args, **kwargs) -> None:
        autorun = kwargs.pop("autorun", False)

        if len(args) == 1 and isinstance(args[0], Mapping) and not kwargs:
            mapping = args[0]
            for topic, func in mapping.items():
                self._register_rpc_service(topic, func)

        elif not args and set(kwargs) == {"topic", "function"}:
            self._register_rpc_service(kwargs["topic"], kwargs["function"])

        else:
            raise ValueError(
                "Invalid arguments. Use either:\n"
                " - create_rpc_service(topic='topic', function=func)\n"
                " - create_rpc_service({'topic': func, 'topic2': func2})"
            )
        if autorun:
            self._service_provider.run()

    def run(self) -> None:
        self._service_provider.run()

    def consume_message(
        self,
        topic: Optional[str] = None,
        amount: int = 1,
        timeout: Optional[float] = None,
    ) -> Union[Optional[Message], list[Optional[Message]]]:
        if not isinstance(amount, int) or amount < 1:
            raise ValueError("amount must be greater than or equal to 1.")
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be greater than or equal to 0.")
        if amount > 1 and timeout is None:
            raise ValueError(
                "timeout is required when amount is greater than 1."
            )

        if topic is not None:
            self._subscribe_once(topic)
        consumed_messages = []

        while len(consumed_messages) < amount:
            try:
                msg = self._channel.consume(timeout=timeout)
                consumed_messages.append(msg)
            except socket.timeout:
                consumed_messages.append(None)
        return consumed_messages if amount >= 2 else consumed_messages[0]

    def publish(self, topic: Union[str, list[str]], message: Message) -> None:
        if not isinstance(message, Message):
            raise ValueError("message must be an is_wire.core.Message.")

        for t in self._normalize_topics(topic):
            self._channel.publish(topic=t, message=message)

    def close(self) -> None:
        self._channel.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False
