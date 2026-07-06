"""Structured logging via loguru: JSON in prod, human-readable in dev."""

from __future__ import annotations

import sys

from loguru import logger

from app.core.config import get_settings


def configure_logging() -> None:
    """Reset loguru sinks and configure based on environment.

    - prod: JSON lines to stdout (ready for log aggregation).
    - dev/test: colorized human-readable to stderr.
    """
    settings = get_settings()
    logger.remove()

    if settings.is_prod:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            serialize=True,  # JSON output
            backtrace=False,
            diagnose=False,
        )
    else:
        logger.add(
            sys.stderr,
            level=settings.log_level,
            colorize=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            backtrace=True,
            diagnose=not settings.is_prod,
        )


__all__ = ["configure_logging", "logger"]
