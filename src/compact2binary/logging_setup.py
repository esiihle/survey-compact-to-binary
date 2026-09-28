"""Logging setup for the CLI.

Status messages go through logging (to stderr) so they stay separate from
actual data output (which goes to stdout or a file). ``--verbose`` and
``--quiet`` shift the level without changing any call sites.
"""

from __future__ import annotations

import logging
import sys

LOGGER_NAME = "compact2binary"


def configure_logging(verbose: bool = False, quiet: bool = False) -> logging.Logger:
    """Configure and return the package logger.

    Precedence: ``quiet`` (warnings only) overrides ``verbose`` (debug), and
    the default is INFO.
    """
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(level=level, format="%(message)s", stream=sys.stderr)
    return logging.getLogger(LOGGER_NAME)
