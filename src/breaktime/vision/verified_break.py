"""Closed-loop break verification -- this project's core differentiator.

A break is not "complete" because the user dismissed a notification; it's complete
because the vision pipeline observed them actually look away from the screen for the
configured duration. See core/types.py (BreakEvent) for the resulting record.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from breaktime.core.types import BreakEvent, DetectionResult, TriggerReason


@dataclass
class VerifiedBreakTracker:
    """Feed DetectionResults in via `observe` while a break is pending/in-progress."""

    required_away_seconds: float
    trigger_reason: TriggerReason
    _started_at: float = field(default_factory=time.time)
    _away_since: float | None = None
    _completed_at: float | None = None

    @property
    def is_verified(self) -> bool:
        return self._completed_at is not None

    def observe(self, result: DetectionResult) -> None:
        if self.is_verified:
            return

        # No face at all (stepped away) counts as "looking away" -- that's a real break.
        looking_away = (not result.face_present) or (result.gaze_on_screen is False)

        if looking_away:
            if self._away_since is None:
                self._away_since = result.timestamp
            elif result.timestamp - self._away_since >= self.required_away_seconds:
                self._completed_at = result.timestamp
        else:
            self._away_since = None

    def to_event(self) -> BreakEvent:
        return BreakEvent(
            trigger_reason=self.trigger_reason,
            started_at=self._started_at,
            completed_at=self._completed_at,
            verified=self.is_verified,
        )
