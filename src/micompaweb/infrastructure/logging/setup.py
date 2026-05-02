"""Setup de logging estructurado con structlog."""
import logging
import sys
from typing import Any

import structlog


def configure_logging(
    level: str = "INFO",
    json_format: bool = False,
    cache_logger_on_first_use: bool = True,
) -> None:
    """Configura structlog y logging stdlib.

    Args:
        level: Nivel de log (DEBUG, INFO, WARNING, ERROR).
        json_format: Si True, output JSON (para produccion). Si False, consola legible.
        cache_logger_on_first_use: Cachear loggers para performance.
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.stdlib.add_logger_name,
    ]

    if json_format:
        formatter = structlog.processors.JSONRenderer()
    else:
        formatter = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ExtraAdder(),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=cache_logger_on_first_use,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        force=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Obtiene un logger estructurado."""
    return structlog.get_logger(name)
