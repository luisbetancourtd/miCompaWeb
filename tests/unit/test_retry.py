"""Tests para infrastructure/retry.py."""
import pytest
from unittest.mock import Mock, patch

from micompaweb.infrastructure.retry import with_retry, api_retry, critical_retry


class TestWithRetry:
    def test_success_on_first_attempt(self):
        """Si la funcion funciona, no reintenta."""
        mock_func = Mock(return_value="ok")

        @with_retry(max_attempts=3)
        def wrapped():
            return mock_func()

        result = wrapped()
        assert result == "ok"
        assert mock_func.call_count == 1

    def test_retry_on_exception(self):
        """Reintenta hasta que funciona."""
        mock_func = Mock(side_effect=[RuntimeError("fail"), RuntimeError("fail"), "ok"])

        @with_retry(max_attempts=3, backoff_base=0.01)
        def wrapped():
            return mock_func()

        result = wrapped()
        assert result == "ok"
        assert mock_func.call_count == 3

    def test_raises_after_max_attempts(self):
        """Si agota intentos, lanza la ultima excepcion."""
        mock_func = Mock(side_effect=RuntimeError("final"))

        @with_retry(max_attempts=2, backoff_base=0.01)
        def wrapped():
            return mock_func()

        with pytest.raises(RuntimeError, match="final"):
            wrapped()

        assert mock_func.call_count == 2

    def test_respects_max_seconds(self):
        """Si supera max_seconds, aborta."""
        mock_func = Mock(side_effect=RuntimeError("slow"))

        @with_retry(max_attempts=100, max_seconds=0.05, backoff_base=0.02)
        def wrapped():
            return mock_func()

        with pytest.raises(RuntimeError):
            wrapped()
        assert mock_func.call_count < 100  # No llego al max_attempts

    def test_fixed_wait_strategy(self):
        mock_func = Mock(side_effect=[RuntimeError("fail"), "ok"])

        @with_retry(max_attempts=3, wait_strategy="fixed", backoff_base=0.01)
        def wrapped():
            return mock_func()

        assert wrapped() == "ok"
        assert mock_func.call_count == 2

    def test_exception_filter(self):
        """Solo captura excepciones especificadas."""
        mock_func = Mock(side_effect=ValueError("wrong type"))

        @with_retry(max_attempts=3, backoff_base=0.01, exceptions=(RuntimeError,))
        def wrapped():
            return mock_func()

        with pytest.raises(ValueError):
            wrapped()
        assert mock_func.call_count == 1  # No reintento


class TestApiRetry:
    def test_default_decorator_applies(self):
        call_count = 0

        @api_retry
        def flaky_api():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("timeout")
            return "success"

        with patch("micompaweb.infrastructure.retry.logger"):
            assert flaky_api() == "success"
            assert call_count == 2

    def test_default_does_not_retry_on_valueerror(self):
        """api_retry por defecto no captura ValueError."""
        call_count = 0

        @api_retry
        def bad_value():
            nonlocal call_count
            call_count += 1
            raise ValueError("no retry")

        with patch("micompaweb.infrastructure.retry.logger"):
            with pytest.raises(ValueError):
                bad_value()
            assert call_count == 1


class TestCriticalRetry:
    def test_more_attempts(self):
        call_count = 0

        @critical_retry
        def very_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("fail")
            return "done"

        with patch("micompaweb.infrastructure.retry.logger"):
            assert very_flaky() == "done"
            assert call_count == 3
