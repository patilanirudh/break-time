"""Continuous-screen-time state machine.

Tracks how long the user has been continuously facing the screen, flags fatigue when
blink rate drops meaningfully below their calibrated baseline, and reports when a break
should be triggered. Owns only state derived from DetectionResults -- no camera access,
which is what makes it fully unit-testable with synthetic fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from breaktime.core.types import (
    CalibrationProfile,
    DetectionResult,
    FatigueSignal,
    SessionPhase,
    TriggerReason,
)

_BLINK_RATE_WINDOW_SECONDS = 60.0
_AWAY_RESET_SECONDS = 5.0


@dataclass
class SessionTracker:
    """Drives phase transitions from a stream of DetectionResults + user thresholds."""

    continuous_time_threshold_seconds: float
    fatigue_blink_rate_drop_ratio: float
    calibration: CalibrationProfile

    phase: SessionPhase = SessionPhase.ACTIVE
    _screen_time_started_at: float | None = None
    _away_since: float | None = None
    _recent_blink_timestamps: list[float] = field(default_factory=list)
    _was_open: bool = True

    def observe(self, result: DetectionResult) -> TriggerReason | None:
        """Feed one DetectionResult in. Returns a TriggerReason if a break should start."""
        if not result.face_present:
            self._handle_away(result.timestamp)
            return None

        self._away_since = None
        if self._screen_time_started_at is None:
            self._screen_time_started_at = result.timestamp
            self.phase = SessionPhase.ACTIVE

        self._track_blinks(result)

        continuous_seconds = result.timestamp - self._screen_time_started_at
        if continuous_seconds >= self.continuous_time_threshold_seconds:
            return TriggerReason.TIME_THRESHOLD

        if self._fatigue_signal(result.timestamp).is_fatigued:
            return TriggerReason.FATIGUE

        return None

    def start_break(self) -> None:
        self.phase = SessionPhase.BREAK_PENDING

    def reset_after_break(self) -> None:
        self.phase = SessionPhase.ACTIVE
        self._screen_time_started_at = None
        self._recent_blink_timestamps.clear()

    def _handle_away(self, timestamp: float) -> None:
        if self._away_since is None:
            self._away_since = timestamp
        elif timestamp - self._away_since >= _AWAY_RESET_SECONDS:
            self.phase = SessionPhase.AWAY
            self._screen_time_started_at = None
            self._recent_blink_timestamps.clear()

    def _track_blinks(self, result: DetectionResult) -> None:
        if result.ear is None:
            return
        is_open = result.ear >= self.calibration.blink_ear_threshold
        if self._was_open and not is_open:
            self._recent_blink_timestamps.append(result.timestamp)
        self._was_open = is_open

        cutoff = result.timestamp - _BLINK_RATE_WINDOW_SECONDS
        self._recent_blink_timestamps = [t for t in self._recent_blink_timestamps if t >= cutoff]

    def _fatigue_signal(self, now: float) -> FatigueSignal:
        window_minutes = _BLINK_RATE_WINDOW_SECONDS / 60.0
        current_rate = len(self._recent_blink_timestamps) / window_minutes
        threshold = self.calibration.baseline_blink_rate_per_min * (
            1 - self.fatigue_blink_rate_drop_ratio
        )
        # Require close to a full window of *elapsed session time* before judging fatigue
        # -- keyed off the session start, not the blink buffer's contents, so a
        # genuinely low/zero blink rate is still correctly judged once enough real time
        # has passed (an empty buffer must not be read as "the window is already full").
        has_full_window = (
            self._screen_time_started_at is not None
            and now - self._screen_time_started_at >= _BLINK_RATE_WINDOW_SECONDS * 0.9
        )
        is_fatigued = has_full_window and current_rate < threshold
        return FatigueSignal(
            is_fatigued=is_fatigued,
            current_blink_rate_per_min=current_rate,
            baseline_blink_rate_per_min=self.calibration.baseline_blink_rate_per_min,
        )
