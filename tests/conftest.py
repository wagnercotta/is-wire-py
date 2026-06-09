import os
import uuid

import pytest
from is_wire.core import Channel
from is_wire.enhancement import IsWireEnhanced

URI = os.getenv("WIRE_RABBITMQ_URI", "amqp://guest:guest@localhost:5672")
EXCHANGE = os.getenv("WIRE_DEFAULT_EXCHANGE", "is")


@pytest.fixture(scope="function")
def channel():
    """Fixture that provides a Channel connected to RabbitMQ."""
    ch = Channel(uri=URI, exchange=EXCHANGE)
    yield ch
    ch.close()


@pytest.fixture(scope="function")
def enhanced():
    """Fixture that provides an IsWireEnhanced instance."""
    e = IsWireEnhanced(
        user="guest",
        password="guest",
        host="localhost",
        port=5672,
    )
    yield e
    e.close()


@pytest.fixture
def topic():
    """Fixture that generates a unique topic name."""
    return f"test.topic.{uuid.uuid4()}"
