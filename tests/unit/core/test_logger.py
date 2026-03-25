import logging

import pytest
from is_wire.core import Logger


def test_logger_creation():
    logger = Logger("TestLogger")
    assert logger.logger is not None
    assert logger.logger.name == "TestLogger"


def test_logger_level_constants():
    assert Logger.DEBUG == logging.DEBUG
    assert Logger.INFO == logging.INFO
    assert Logger.WARN == logging.WARN
    assert Logger.ERROR == logging.ERROR
    assert Logger.CRITICAL == logging.CRITICAL


def test_logger_set_level():
    logger = Logger("TestLevel")
    logger.set_level(Logger.ERROR)
    assert logger.logger.level == logging.ERROR


def test_logger_debug(capfd):
    logger = Logger("DebugTest", level=Logger.DEBUG)
    logger.debug("Debug message {}", "arg1")
    captured = capfd.readouterr()
    assert "Debug message arg1" in captured.err


def test_logger_info(capfd):
    logger = Logger("InfoTest", level=Logger.INFO)
    logger.info("Info message {}", "arg1")
    captured = capfd.readouterr()
    assert "Info message arg1" in captured.err


def test_logger_warn(capfd):
    logger = Logger("WarnTest", level=Logger.WARN)
    logger.warn("Warn message {}", "arg1")
    captured = capfd.readouterr()
    assert "Warn message arg1" in captured.err


def test_logger_error(capfd):
    logger = Logger("ErrorTest", level=Logger.ERROR)
    logger.error("Error message {}", "arg1")
    captured = capfd.readouterr()
    assert "Error message arg1" in captured.err


def test_logger_invalid_name():
    with pytest.raises(TypeError):
        Logger(123)


def test_logger_empty_name():
    logger = Logger("")
    assert logger.logger is not None
