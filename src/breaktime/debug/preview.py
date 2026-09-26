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
from breaktime.vision.gaze import GazeMonitor

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

        remaining = session.current_phase_remaining_seconds
        _draw_overlay(
            frame,
            [
                f"CALIBRATING: {session.current_instruction} ({remaining:0.0f}s left)",
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
    gaze_monitor = GazeMonitor(profile)
    for frame in frames(capture, settings.capture_fps):
        detection, mood = detector.analyze(frame, include_mood=settings.mood_hint_enabled)
        lines = _status_lines(detection, profile, gaze_monitor)
        if mood is not None:
            lines.append(f"tension_hint={_fmt(mood.tension_score)} (experimental)")

        _draw_overlay(frame, lines)
        cv2.imshow(_WINDOW_NAME, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break


def _status_lines(
    detection: DetectionResult, profile: CalibrationProfile, gaze_monitor: GazeMonitor
) -> list[str]:
    on_screen = gaze_monitor.judge(detection)
    yaw_r, pitch_r = profile.on_screen_yaw_range, profile.on_screen_pitch_range
    yaw_line = (
        f"head_yaw={_fmt(detection.head_yaw_deg)} (ok {yaw_r.minimum:.1f}..{yaw_r.maximum:.1f})  "
        f"pitch={_fmt(detection.head_pitch_deg)} (ok {pitch_r.minimum:.1f}..{pitch_r.maximum:.1f})"
    )
    gaze_h_r = profile.on_screen_gaze_horizontal_range
    gaze_v_r = profile.on_screen_gaze_vertical_range
    gaze_line = (
        f"gaze_h={_fmt(detection.gaze_horizontal_ratio)} "
        f"(ok {gaze_h_r.minimum:.2f}..{gaze_h_r.maximum:.2f})  "
        f"gaze_v={_fmt(detection.gaze_vertical_ratio)} "
        f"(ok {gaze_v_r.minimum:.2f}..{gaze_v_r.maximum:.2f})"
    )
    return [
        f"face_present={detection.face_present}",
        f"ear={_fmt(detection.ear)}  blink_threshold={profile.blink_ear_threshold:.3f}",
        f"looking_at_screen={on_screen}",
        yaw_line,
        gaze_line,
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
