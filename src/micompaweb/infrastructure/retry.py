"""Retry decorators con tenacity para APIs y operaciones fragiles."""
from functools import wraps
from typing import Any, Callable, Optional, Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential,
    wait_fixed,
)

import logging

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    max_seconds: Optional[float] = None,
    backoff_base: float = 1.0,
    backoff_max: float = 10.0,
    exceptions: tuple[Type[BaseException], ...] = (Exception,),
    wait_strategy: str = "exponential",
    log_before_sleep: bool = True,
) -> Callable[..., Any]:
    """Decorator configurable con tenacity.

    Args:
        max_attempts: Numero maximo de reintentos.
        max_seconds: Tiempo maximo total de espera (None = sin limite).
        backoff_base: Segundos base para backoff exponencial.
        backoff_max: Tope de segundos entre reintentos.
        exceptions: Tupla de excepciones a capturar.
        wait_strategy: 'exponential' o 'fixed'.
        log_before_sleep: Si True, loguea antes de cada espera.
    """
    stop = stop_after_attempt(max_attempts)
    if max_seconds is not None:
        stop = stop | stop_after_delay(max_seconds)

    wait = (
        wait_exponential(multiplier=backoff_base, max=backoff_max)
        if wait_strategy == "exponential"
        else wait_fixed(backoff_base)
    )

    kwargs = dict(
        stop=stop,
        wait=wait,
        retry=retry_if_exception_type(exceptions),
        reraise=True,
    )
    if log_before_sleep:
        kwargs["before_sleep"] = _log_retry_attempt

    return retry(**kwargs)


def _log_retry_attempt(retry_state):
    """Callback simple para loguear antes de cada reintento."""
    err = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "Reintentando %s tras error %s (intento %d)",
        retry_state.fn.__name__ if retry_state.fn else "funcion",
        err.__class__.__name__ if err else "?",
        retry_state.attempt_number,
    )


def api_retry(func: Callable[..., Any]) -> Callable[..., Any]:
    """Default para llamadas HTTP: 3 intentos, backoff 1-10s, captura OSError/ConnectionError."""
    decorator = with_retry(
        max_attempts=3,
        backoff_base=1.0,
        backoff_max=10.0,
        exceptions=(OSError, ConnectionError, TimeoutError),
    )
    return decorator(func)


def critical_retry(func: Callable[..., Any]) -> Callable[..., Any]:
    """Para operaciones criticas: 5 intentos, hasta 60s total."""
    decorator = with_retry(
        max_attempts=5,
        max_seconds=60.0,
        backoff_base=2.0,
        backoff_max=15.0,
        exceptions=(OSError, ConnectionError, TimeoutError, RuntimeError),
    )
    return decorator(func)
