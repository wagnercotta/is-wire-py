import pytest
from is_wire.core import ContentType
from is_wire.core.wire.content_type import (
    content_type_from_wire,
    content_type_to_wire,
)


def test_content_type_enum_values():
    # PROTOBUF = 1, JSON = 2 (not 0-indexed)
    assert ContentType.PROTOBUF.value == 1
    assert ContentType.JSON.value == 2


def test_content_type_to_wire_protobuf():
    result = content_type_to_wire(ContentType.PROTOBUF)
    assert result == "application/x-protobuf"


def test_content_type_to_wire_json():
    result = content_type_to_wire(ContentType.JSON)
    assert result == "application/json"


def test_content_type_to_wire_invalid_type():
    with pytest.raises(TypeError, match="content_type"):
        content_type_to_wire("invalid")


def test_content_type_from_wire_protobuf():
    result = content_type_from_wire("application/x-protobuf")
    assert result == ContentType.PROTOBUF


def test_content_type_from_wire_json():
    result = content_type_from_wire("application/json")
    assert result == ContentType.JSON


def test_content_type_from_wire_invalid():
    with pytest.raises(RuntimeError, match="Bad content_type"):
        content_type_from_wire("text/plain")


def test_content_type_from_wire_invalid_type():
    with pytest.raises(TypeError):
        content_type_from_wire(123)


def test_content_type_roundtrip_protobuf():
    original = ContentType.PROTOBUF
    wire = content_type_to_wire(original)
    result = content_type_from_wire(wire)
    assert result == original


def test_content_type_roundtrip_json():
    original = ContentType.JSON
    wire = content_type_to_wire(original)
    result = content_type_from_wire(wire)
    assert result == original
