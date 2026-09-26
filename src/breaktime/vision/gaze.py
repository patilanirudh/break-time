"""Decides whether the user is looking at the screen, relative to their own calibrated
on-screen ranges -- not a fixed universal angle/position.

This is deliberately separate from vision/detection.py: detection.py only ever produces
raw per-frame signals (head yaw/pitch, eye-in-socket ratios); judging what those signals
*mean* requires a CalibrationProfile, which detection.py never sees.
"""

from __future__ import annotations

from breaktime.core.types import CalibrationProfile, DetectionResult


def is_looking_at_screen(detection: DetectionResult, profile: CalibrationProfile) -> bool | None:
    """True/False if we can judge; None if we don't have a reliable signal this frame.

    Live testing found that a single frame's eye-in-socket ratio is unreliable during a
    blink: as the eyelid closes/opens, the visible iris shifts or partially disappears,
    producing outlier readings (observed live: a vertical ratio of -0.04, well outside
    any real range) that would otherwise be read as a large, spurious "looking away."
    Since the per-user blink threshold is already calibrated (see
    vision/calibration.py), a blink is simply "ear below that threshold" -- cheap to
    exclude with data we already have. Callers must treat None as "no information this
    frame," not as either on- or off-screen (see vision/verified_break.py).
    """
    if not detection.face_present:
        return None
    if (
        detection.head_yaw_deg is None
        or detection.head_pitch_deg is None
        or detection.gaze_horizontal_ratio is None
        or detection.gaze_vertical_ratio is None
    ):
        return None
    if detection.ear is not None and detection.ear < profile.blink_ear_threshold:
        return None

    return (
        profile.on_screen_yaw_range.contains(detection.head_yaw_deg)
        and profile.on_screen_pitch_range.contains(detection.head_pitch_deg)
        and profile.on_screen_gaze_horizontal_range.contains(detection.gaze_horizontal_ratio)
        and profile.on_screen_gaze_vertical_range.contains(detection.gaze_vertical_ratio)
    )
