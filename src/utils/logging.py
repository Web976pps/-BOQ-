"""Logging utilities wrapping *loguru* setup."""

from __future__ import annotations

import sys
from typing import Literal

from loguru import logger


def setup_logging(
    *,
    json_logging: bool = False,
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
) -> None:  # noqa: D401
    """Configure global *loguru* logger.

    Parameters
    ----------
    json_logging:
        Emit logs as newline-delimited JSON when *True* (suitable for log
        aggregation). When *False*, logs are pretty-formatted.
    level:
        Minimum log severity.
    """

    # Remove any previous handlers configured by other modules/tests
    logger.remove()

    logger.add(
        sys.stderr,
        level=level.upper(),
        serialize=json_logging,
        backtrace=False,
        diagnose=False,
    )
