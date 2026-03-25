import uuid
from datetime import datetime, timezone
from platform import uname


def new_uuid():
    return uuid.uuid4().int >> 64


def consumer_id():
    return "{}/{:X}".format(uname()[1], new_uuid())


def now():
    return datetime.now(timezone.utc).timestamp()


def assert_type(instance, types, name):
    if isinstance(types, list):
        types = tuple(types)

    if not isinstance(instance, types):
        input_type = type(instance).__name__
        if isinstance(types, tuple):
            types = " or ".join([t.__name__ for t in types])
            error = "Object {} must be of types {}, received type {}".format(
                name, types, input_type
            )
        else:
            error = "Object {} must be of type {}, received type {}".format(
                name, types.__name__, input_type
            )
        raise TypeError(error)
