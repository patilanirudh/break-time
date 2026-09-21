"""Live debug preview window (`breaktime --debug-preview`).

An opt-in, visual verification tool: shows the raw camera feed with the live detection
numbers overlaid (EAR, blink threshold, gaze-on-screen, head pose, fatigue baseline), so
you can see exactly what the pipeline is measuring, in real time, instead of only reading
numbers out of the log file after the fact.

Nothing shown here is ever saved to disk or sent anywhere -- it is a live window on your
own screen, exactly like any other webcam preview app, closed with 'q' or the window's
close button. This is a separate mode from the normal background tray app, which never
displays camera output at all.
"""

from __future__ import annotations

import cv2

from breaktime.config.settings import BreakTimeSettings
from breaktime.core.types import CalibrationProfile, DetectionResult
from breaktime.vision.calibration import CalibrationSession
from breaktime.vision.capture import Frame, frames, open_camera
from breaktime.vision.detection import FaceDetector

_WINDOW_NAME = "Break-Time debug preview (press q to quit)"
_TEXT_COLOR = (0, 255, 0)


def run() -> None:
    settings = BreakTimeSettings.load()
    with open_camera() as capture, FaceDetector() as detector:
        profile = _calibrate_with_preview(detector, capture, settings)
        if profile is not None:
            _detect_with_preview(detector, capture, settings, profile)
    cv2.destroyAllWindows()


def _calibrate_with_preview(
    detector: FaceDetector, capture: cv2.VideoCapture, settings: BreakTimeSettings
) -> CalibrationProfile | None:
    session = CalibrationSession()
    for frame in frames(capture, settings.capture_fps):
        detection, _ = detector.analyze(frame)
        session.observe(detection)

        remaining = max(0.0, session.duration_seconds - session.elapsed_seconds)
        _draw_overlay(
            frame,
            [
                f"CALIBRATING -- look at the screen normally ({remaining:0.0f}s left)",
                f"face_present={detection.face_present}  ear={_fmt(detection.ear)}",
            ],
        )
        cv2.imshow(_WINDOW_NAME, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            return None

        if session.is_complete:
            break

    return session.finish()


def _detect_with_preview(
    detector: FaceDetector,
    capture: cv2.VideoCapture,
    settings: BreakTimeSettings,
    profile: CalibrationProfile,
) -> None:
    for frame in frames(capture, settings.capture_fps):
        detection, mood = detector.analyze(frame, include_mood=settings.mood_hint_enabled)
        lines = _status_lines(detection, profile)
        if mood is not None:
            lines.append(f"tension_hint={_fmt(mood.tension_score)} (experimental)")

        _draw_overlay(frame, lines)
        cv2.imshow(_WINDOW_NAME, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


def _status_lines(detection: DetectionResult, profile: CalibrationProfile) -> list[str]:
    return [
        f"face_present={detection.face_present}",
        f"ear={_fmt(detection.ear)}  blink_threshold={profile.blink_ear_threshold:.3f}",
        f"gaze_on_screen={detection.gaze_on_screen}",
        f"head_yaw={_fmt(detection.head_yaw_deg)}  head_pitch={_fmt(detection.head_pitch_deg)}",
        f"baseline_blink_rate={profile.baseline_blink_rate_per_min:.1f}/min",
    ]


def _fmt(value: float | None) -> str:
    return f"{value:.3f}" if value is not None else "None"


def _draw_overlay(frame: Frame, lines: list[str]) -> None:
    for i, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (10, 24 + i * 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            _TEXT_COLOR,
            1,
            cv2.LINE_AA,
        )
