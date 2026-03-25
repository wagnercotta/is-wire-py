
# is-wire

[![PyPI](https://img.shields.io/pypi/v/is-wire.svg?style=for-the-badge)](https://pypi.org/project/is-wire/)
[![Build](https://img.shields.io/github/actions/workflow/status/labvisio/is-wire-py/main.yml?style=for-the-badge)](https://github.com/labvisio/is-wire-py/actions)
[![Python suport](https://img.shields.io/pypi/pyversions/is-wire?style=for-the-badge)](https://pypi.org/project/is-wire)
[![Downloads](https://img.shields.io/pypi/dm/is-wire?style=for-the-badge)](https://pypi.org/project/is-wire/)

Pub/Sub middleware for the *is* architecture (python implementation)

## Installation 

Install the wire package using `pip` or `pipenv`:

```shell
  pip install --user is-wire
  # or
  pipenv install --user is-wire
```

## Usage

### Prepare environment

In order to send/receive messages an amqp broker is necessary, to create one simply run:

```shell
docker run -d --rm -p 5672:5672 -p 15672:15672 rabbitmq:3.7.6-management
```

### Basic send/receive

Create a channel to connect to a broker, create a subscription and subscribe to desired topics to receive messages:

```python
from is_wire.core import Channel, Subscription

# Connect to the broker
channel = Channel("amqp://guest:guest@localhost:5672")

# Subscribe to the desired topic(s)
subscription = Subscription(channel)
subscription.subscribe(topic="MyTopic.SubTopic")
# ... subscription.subscribe(topic="Other.Topic")

# Blocks forever waiting for one message from any subscription
message = channel.consume()
print(message)
```

Create and publish messages:

```python
from is_wire.core import Channel, Message

# Connect to the broker
channel = Channel("amqp://guest:guest@localhost:5672")

message = Message()
# Body is a binary field therefore we need to encode the string
message.body = "Hello!".encode('latin1')

# Broadcast message to anyone interested (subscribed)
channel.publish(message, topic="MyTopic.SubTopic")
```

Serialize/Deserialize protobuf objects:

```python
from is_wire.core import Channel, Message, Subscription, ContentType
from google.protobuf.struct_pb2 import Struct

channel = Channel("amqp://guest:guest@localhost:5672")

subscription = Subscription(channel)
subscription.subscribe(topic="MyTopic.SubTopic")

struct = Struct()
struct.fields["apples"].string_value = "red"

message = Message()
message.content_type = ContentType.JSON # or ContentType.PROTOBUF
message.pack(struct) # Serialize the struct into the message body

channel.publish(message, topic="MyTopic.SubTopic")

# Blocks forever waiting for the message we just sent
received_message = channel.consume()
# Deserialize the struct from the message body
received_struct = received_message.unpack(Struct) 

# Check that they are equal
assert struct == received_struct
```

### Basic Request/Reply 

Create a RPC Server:

```python
from is_wire.core import Channel, StatusCode, Status
from is_wire.rpc import ServiceProvider, LogInterceptor
from google.protobuf.struct_pb2 import Struct
import time


def increment(struct, ctx):
    if struct.fields["value"].number_value < 0:
        # Return error to client
        return Status(StatusCode.INVALID_ARGUMENT, "Number must be positive")

    time.sleep(0.2)  # Simulate work
    struct.fields["value"].number_value += 1.0
    # Return normal reply
    return struct


channel = Channel("amqp://guest:guest@localhost:5672")

provider = ServiceProvider(channel)
logging = LogInterceptor()  # Log requests to console
provider.add_interceptor(logging)

provider.delegate(
    topic="MyService.Increment",
    function=increment,
    request_type=Struct,
    reply_type=Struct)

provider.run() # Blocks forever processing requests
```

Send a request to the RPC Server:

```python
from is_wire.core import Channel, Message, Subscription
from google.protobuf.struct_pb2 import Struct
import socket

channel = Channel("amqp://guest:guest@localhost:5672")
subscription = Subscription(channel)

# Prepare request
struct = Struct()
struct.fields["value"].number_value = 1.0
request = Message(content=struct, reply_to=subscription)
# Make request
channel.publish(request, topic="MyService.Increment")

# Wait for reply with 1.0 seconds timeout
try:
    reply = channel.consume(timeout=1.0)
    struct = reply.unpack(Struct)
    print('RPC Status:', reply.status, '\nReply:', struct)
except socket.timeout:
    print('No reply :(')
```

Multiples requests can be done throughout same client. To distinguish which reply is related to each request, you can use the `correlation_id`. This attribute is always set when a `Message` is published containing `reply_to` parameter, which means that it was a RPC request. Example below shows how to deal with it.

```python
from is_wire.core import Channel, Message, Subscription
from google.protobuf.struct_pb2 import Struct
import socket

channel = Channel("amqp://guest:guest@localhost:5672")
subscription = Subscription(channel)

# Prepare first request
struct = Struct()
struct.fields["value"].number_value = 1.0
request_1 = Message(content=struct, reply_to=subscription)

# Prepare second request
struct = Struct()
struct.fields["value"].number_value = 2.0
request_2 = Message(content=struct, reply_to=subscription)

# Make requests
channel.publish(request_1, topic="MyService.Increment")
channel.publish(request_2, topic="MyService.Increment")

# Wait for replies with 1.0 seconds timeout
n_replies = 0
while n_replies < 2:
    try:
        reply = channel.consume(timeout=1.0)
        struct = reply.unpack(Struct)
        if reply.correlation_id == request_1.correlation_id:
            n_replies += 1
            print('First Request\nRPC Status:', reply.status, '\nReply:', struct)
        elif reply.correlation_id == request_2.correlation_id:
            n_replies += 1
            print('Second Request\nRPC Status:', reply.status, '\nReply:', struct)
        else:
            print('Unexpected message')
    except socket.timeout:
        print('No reply :(')
```

### Enhanced API (IsWireEnhanced)

The `IsWireEnhanced` class provides a simplified, high-level API for common messaging patterns. It reduces boilerplate code by using type annotations to automatically configure request/reply types.

#### Creating an enhanced connection

```python
from is_wire.enhancement import IsWireEnhanced

# Connect using individual parameters
wire = IsWireEnhanced(
    user="guest",
    password="guest",
    host="localhost",
    port=5672
)
```

#### Creating RPC services with automatic type inference

Functions registered as RPC services must have type annotations for both parameters and return types. The enhanced API automatically extracts these types:

```python
from is_wire.enhancement import IsWireEnhanced
from google.protobuf.wrappers_pb2 import Int64Value, StringValue

wire = IsWireEnhanced(
    user="guest",
    password="guest",
    host="localhost",
    port=5672
)


# Type annotations are required - they define request/reply types
def double_value(request: Int64Value) -> Int64Value:
    return Int64Value(value=request.value * 2)


def to_string(request: Int64Value) -> StringValue:
    return StringValue(value=str(request.value))


# Register multiple services at once using a dictionary
wire.create_rpc_service({
    "Math.Double": double_value,
    "Math.ToString": to_string,
})

# Or register a single service using keyword arguments
wire.create_rpc_service(topic="Math.Double", function=double_value)

# Start processing requests (blocks forever)
wire.run()
```

#### Publishing messages

```python
from is_wire.enhancement import IsWireEnhanced
from is_wire.core import Message

wire = IsWireEnhanced(
    user="guest",
    password="guest",
    host="localhost",
    port=5672
)

message = Message()
message.body = "Hello!".encode('latin1')

# Publish to a single topic
wire.publish("MyTopic.SubTopic", message)

# Publish to multiple topics at once
wire.publish(["Topic1", "Topic2", "Topic3"], message)
```

#### Consuming messages

```python
from is_wire.enhancement import IsWireEnhanced

wire = IsWireEnhanced(
    user="guest",
    password="guest",
    host="localhost",
    port=5672
)

# Consume a single message (blocks until received)
message = wire.consume_message("MyTopic.SubTopic")

# Consume with timeout (returns None if no message received)
message = wire.consume_message("MyTopic.SubTopic", timeout=5)

# Consume multiple messages
messages = wire.consume_message("MyTopic.SubTopic", amount=3, timeout=10)
# Returns a list of 3 messages (or None for timeouts)
```

## Development

### Prerequisites

- Python 3.9 or higher
- Docker (for running RabbitMQ)
- pip or pipenv

### Setting up the development environment

```shell
# Clone the repository
git clone https://github.com/labvisio/is-wire-py.git
cd is-wire-py

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package in development mode with test dependencies
pip install -e .
pip install -r requirements-test.txt
```

### Running RabbitMQ

Integration tests require a running RabbitMQ instance:

```shell
docker run -d --rm -p 5672:5672 -p 15672:15672 rabbitmq:4.2.5-management
```

The RabbitMQ management UI will be available at http://localhost:15672 (guest/guest).

### Running tests

```shell
# Run all tests with tox (recommended for CI)
pip install tox
tox

```


### Making changes

1. Create a new branch for your feature or fix
2. Make your changes and add tests
3. Run the test suite to ensure nothing is broken
4. Submit a pull request


## Changelog

### [2.0.0] - 2026-03-25

#### Added
- **IsWireEnhanced API**: New simplified interface for common messaging patterns
  - Automatic URI construction and validation
  - RPC service creation with type inference from function annotations
  - Multi-topic publish support
  - Simplified message consumption with timeout and batch support

#### Changed
- **Python version**: Now requires Python 3.9+ (dropped support for Python 2.7 and 3.6-3.8)
- **Packaging**: Migrated from `setup.py` to `pyproject.toml` (PEP 517/518 compliant)
- **Dependencies**: Replaced `six` with native Python 3 equivalents
  - `six.moves.urllib` → `urllib.parse`
  - `six.binary_type` → `bytes`
  - `six.string_types` → `str`
  - `six.raise_from()` → native `raise ... from` syntax
- **Unit Tests**: Unit tests are now separated from integration tests run without RabbitMQ dependency
- **Integration Tests**: New test suite marked with `@pytest.mark.integration` for IsWireEnhanced and RabbitMQ interactions

#### Removed
- **Tracing support**: Removed OpenTelemetry/OpenTracing integration
  - Removed `Tracer` from core
  - Removed `TracingInterceptor` from RPC
  - Removed `extract_tracing()` and `inject_tracing()` methods from Message
  - Removed dependencies: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-opentracing-shim`
- **Python 2 support**: Removed `six` dependency and Python 2 compatibility code

### [1.2.1] - Previous Release
- Last version with tracing support and Python 2.7 compatibility
