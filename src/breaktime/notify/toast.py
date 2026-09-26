"""Windows-native toast notifications via win11toast.

Actionable buttons exist for convenience (snooze), but actual break completion is never
granted by a button click -- only by VerifiedBreakTracker observing real gaze/head-pose
divergence (see vision/verified_break.py). This module only presents UI; it never marks
anything "verified" itself.
"""

from __future__ import annotations

from collections.abc import Callable

from win11toast import notify

from breaktime.core.logging import get_logger, log_event

_logger = get_logger("notify.toast")


def show_break_prompt(*, on_snooze: Callable[[], None] | None = None) -> None:
    """Blocking call -- invoke from a background thread, never the vision loop thread."""
    log_event(_logger, "break_prompt_shown")
    buttons = ["Snooze 5 min"] if on_snooze else []
    result = notify(
        "Time for an eye break",
        "Look at something at least 20 feet away for 20 seconds.",
        buttons=buttons,
    )
    if on_snooze and result == "Snooze 5 min":
        log_event(_logger, "break_snoozed")
        on_snooze()


def show_break_verified() -> None:
    log_event(_logger, "break_verified_toast_shown")
    notify("Nice work", "Break verified, your timer has reset.")


def show_calibration_step(instruction: str, *, seconds: int) -> None:
    """Announces a calibration phase -- the tray app has no window to show this in
    otherwise (unlike --debug-preview, which overlays it on the camera feed directly)."""
    log_event(_logger, "calibration_step_shown", instruction=instruction)
    notify("Break-Time setup", f"{instruction} ({seconds}s)")
