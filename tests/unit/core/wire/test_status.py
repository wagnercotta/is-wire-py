import pytest
from is_wire.core import Status, StatusCode


def test_status_code_values():
    assert StatusCode.UNKNOWN.value == 0
    assert StatusCode.OK.value == 1
    assert StatusCode.CANCELLED.value == 2
    assert StatusCode.INVALID_ARGUMENT.value == 3
    assert StatusCode.DEADLINE_EXCEEDED.value == 4
    assert StatusCode.NOT_FOUND.value == 5
    assert StatusCode.ALREADY_EXISTS.value == 6
    assert StatusCode.PERMISSION_DENIED.value == 7
    assert StatusCode.UNAUTHENTICATED.value == 8
    assert StatusCode.FAILED_PRECONDITION.value == 9
    assert StatusCode.OUT_OF_RANGE.value == 10
    assert StatusCode.UNIMPLEMENTED.value == 11
    assert StatusCode.INTERNAL_ERROR.value == 12


def test_status_default_constructor():
    status = Status()
    assert status.code == StatusCode.UNKNOWN
    assert status.why == ""


def test_status_with_args():
    status = Status(code=StatusCode.OK, why="success")
    assert status.code == StatusCode.OK
    assert status.why == "success"


def test_status_ok_method():
    ok_status = Status(code=StatusCode.OK)
    error_status = Status(code=StatusCode.INTERNAL_ERROR)

    assert ok_status.ok() is True
    assert error_status.ok() is False


def test_status_equality():
    s1 = Status(code=StatusCode.OK, why="test")
    s2 = Status(code=StatusCode.OK, why="test")
    s3 = Status(code=StatusCode.OK, why="different")

    assert s1 == s2
    assert s1 != s3


def test_status_str():
    status = Status(code=StatusCode.NOT_FOUND, why="item missing")
    result = str(status)
    assert "NOT_FOUND" in result
    assert "item missing" in result


def test_status_invalid_code_type():
    with pytest.raises(TypeError, match="code"):
        Status(code="INVALID")


def test_status_invalid_why_type():
    with pytest.raises(TypeError, match="why"):
        Status(code=StatusCode.OK, why=123)


def test_status_setters():
    status = Status()
    status.code = StatusCode.PERMISSION_DENIED
    status.why = "access denied"

    assert status.code == StatusCode.PERMISSION_DENIED
    assert status.why == "access denied"
