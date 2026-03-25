import pytest
from is_wire.core.utils import assert_type, consumer_id, new_uuid, now


def test_new_uuid_returns_int():
    result = new_uuid()
    assert isinstance(result, int)
    assert result >= 0


def test_new_uuid_generates_unique_values():
    uuids = [new_uuid() for _ in range(100)]
    assert len(set(uuids)) == 100


def test_consumer_id_format():
    result = consumer_id()
    assert "/" in result
    parts = result.split("/")
    assert len(parts) == 2
    assert len(parts[0]) > 0  # hostname
    assert len(parts[1]) > 0  # hex uuid


def test_now_returns_float():
    result = now()
    assert isinstance(result, float)
    assert result > 0


def test_now_increases():
    t1 = now()
    t2 = now()
    assert t2 >= t1


def test_assert_type_valid_single():
    assert_type("hello", str, "test")
    assert_type(123, int, "test")
    assert_type(1.5, float, "test")
    assert_type(b"bytes", bytes, "test")
    assert_type([], list, "test")
    assert_type({}, dict, "test")


def test_assert_type_valid_multiple():
    assert_type("hello", [str, int], "test")
    assert_type(123, [str, int], "test")
    assert_type(1.5, [float, int], "test")


def test_assert_type_invalid_single():
    with pytest.raises(TypeError, match="must be of type str"):
        assert_type(123, str, "my_var")


def test_assert_type_invalid_multiple():
    with pytest.raises(TypeError, match="must be of types str or int"):
        assert_type(1.5, [str, int], "my_var")


def test_assert_type_error_message_contains_name():
    with pytest.raises(TypeError, match="my_variable"):
        assert_type([], str, "my_variable")


def test_assert_type_error_message_contains_received_type():
    with pytest.raises(TypeError, match="received type list"):
        assert_type([], str, "test")
