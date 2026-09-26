"""Decides whether the user is looking at the screen, relative to their own calibrated
on-screen ranges -- not a fixed universal angle/position.

This is deliberately separate from vision/detection.py: detection.py only ever produces
raw per-frame signals (head yaw/pitch, eye-in-socket ratios); judging what those signals
*mean* requires a CalibrationProfile, which detection.py never sees.
"""

from __future__ import annotations

from breaktime.core.types import CalibrationProfile, DetectionResult

# A real blink lasts roughly 100-400ms, even a slow one. This is a *duration*, not a
# frame count, so it stays correct regardless of the configured capture_fps (see
# config/settings.py's capture_fps). Live testing found that a hard eyes-only glance at
# an extreme angle can also lower EAR (the visible eyelid shape changes with gaze angle,
# even with the eyes genuinely open) and *sustains* that low reading for as long as the
# glance lasts -- seconds, not milliseconds. Treating any low-EAR frame as "mid-blink,
# discard it" was silently swallowing exactly the glances this module most needs to
# catch. Reused by vision/calibration.py so both places draw the same line.
MAX_BLINK_DURATION_SECONDS = 0.5


class GazeMonitor:
    """Stateful per-attempt gaze judge -- construct one per verification attempt (or
    per debug-preview session) and call `judge` once per frame in order.

    Statefulness is what makes the brief-blink-vs-sustained-glance distinction
    possible: a single frame's EAR alone can't tell them apart, only how long the low
    reading has persisted can.
    """

    def __init__(self, profile: CalibrationProfile) -> None:
        self._profile = profile
        self._low_ear_since: float | None = None

    def judge(self, detection: DetectionResult) -> bool | None:
        """True/False if we can judge; None if we don't have a reliable signal yet
        (no face, missing signals, or still within plausible blink duration)."""
        if not detection.face_present:
            self._low_ear_since = None
            return None
        if (
            detection.head_yaw_deg is None
            or detection.head_pitch_deg is None
            or detection.gaze_horizontal_ratio is None
            or detection.gaze_vertical_ratio is None
        ):
            return None

        if self._is_transient_blink(detection):
            return None

        return (
            self._profile.on_screen_yaw_range.contains(detection.head_yaw_deg)
            and self._profile.on_screen_pitch_range.contains(detection.head_pitch_deg)
            and self._profile.on_screen_gaze_horizontal_range.contains(
                detection.gaze_horizontal_ratio
            )
            and self._profile.on_screen_gaze_vertical_range.contains(detection.gaze_vertical_ratio)
        )

    def _is_transient_blink(self, detection: DetectionResult) -> bool:
        is_low_ear = detection.ear is not None and detection.ear < self._profile.blink_ear_threshold
        if not is_low_ear:
            self._low_ear_since = None
            return False

        if self._low_ear_since is None:
            self._low_ear_since = detection.timestamp
        return detection.timestamp - self._low_ear_since <= MAX_BLINK_DURATION_SECONDS
