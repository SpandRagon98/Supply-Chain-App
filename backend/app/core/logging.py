"""Structured logging configuration."""

import logging
import sys

import structlog


def configure_logging(log_level: str, *, json_logs: bool) -> None:
    """Configure stdlib and structlog with consistent context fields."""

    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(stream=sys.stdout, format="%(message)s", level=level, force=True)

    renderer: structlog.types.Processor
    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=False)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
