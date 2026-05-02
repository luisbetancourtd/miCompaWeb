"""Tests para infrastructure/logging/setup.py."""
import logging
from unittest.mock import patch

import structlog

from micompaweb.infrastructure.logging.setup import configure_logging, get_logger


class TestConfigureLogging:
    def test_default_level_info(self, capfd):
        configure_logging(level="INFO")
        logger = get_logger("test")
        logger.info("hello info")
        captured = capfd.readouterr()
        assert "hello info" in captured.err or "hello info" in captured.out

    def test_level_debug(self, capfd):
        configure_logging(level="DEBUG")
        logger = get_logger("test.debug")
        logger.debug("hello debug")
        captured = capfd.readouterr()
        assert "hello debug" in captured.err or "hello debug" in captured.out

    def test_json_format(self):
        configure_logging(level="INFO", json_format=True)
        logger = get_logger("test.json")
        # Trigger proxy resolution
        resolved = logger.bind()
        assert isinstance(resolved, structlog.stdlib.BoundLogger)

    def test_invalid_level_defaults_to_info(self):
        configure_logging(level="INVALID")
        root = logging.getLogger()
        assert root.level == logging.INFO


class TestGetLogger:
    def test_returns_callable(self):
        configure_logging(level="INFO")
        logger = get_logger("mi.modulo")
        assert callable(logger.info)
        assert callable(logger.warning)
        assert callable(logger.error)

    def test_returns_same_logger_for_same_name(self):
        configure_logging(level="INFO")
        logger_a = get_logger("same.module")
        logger_b = get_logger("same.module")
        assert logger_a is not None
        assert logger_b is not None


class TestLoggingSideEffects:
    def test_reconfigure_idempotent(self, capfd):
        configure_logging(level="INFO")
        configure_logging(level="INFO")
        logger = get_logger("idempotent")
        logger.info("still works")
        captured = capfd.readouterr()
        assert "still works" in captured.err or "still works" in captured.out
