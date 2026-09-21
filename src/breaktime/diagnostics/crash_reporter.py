"""Opt-in-only crash reporting.

Disabled by default and a strict no-op unless the user explicitly enables it in settings
(`crash_reporting_opt_in`). Even when enabled, this never includes camera frames, landmark
data, or per-user identifying information -- only stack traces and coarse app/OS metadata.

`_report` is intentionally not wired to any real external endpoint yet -- there is no
crash-reporting service configured for this project. It exists as the seam a future PR can
wire up (see docs/ROADMAP.md), and stays fully inert until that happens: it never runs
unless `install(enabled=True)` was called, and even then it only logs locally what it
*would* send, so nothing leaves the device silently.
"""

from __future__ import annotations

import platform
import sys
import traceback
from types import TracebackType

from breaktime.core.logging import get_logger, log_event

_logger = get_logger("diagnostics.crash_reporter")


def install(*, enabled: bool) -> None:
    """Install a global excepthook. Always logs locally; only reports if `enabled`."""

    def _handle(
        exc_type: type[BaseException], exc: BaseException, tb: TracebackType | None
    ) -> None:
        trace_text = "".join(traceback.format_exception(exc_type, exc, tb))
        log_event(_logger, "unhandled_exception", exc_type=exc_type.__name__)
        _logger.error(trace_text)

        if enabled:
            _report(exc_type, trace_text)

        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _handle


def _report(exc_type: type[BaseException], trace_text: str) -> None:
    del trace_text  # not transmitted anywhere yet -- see module docstring
    log_event(
        _logger,
        "crash_report_would_send",
        exc_type=exc_type.__name__,
        os=platform.system(),
        os_version=platform.version(),
    )
