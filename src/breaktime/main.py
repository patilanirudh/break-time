"""Entry point: wires capture -> detection -> state -> notify/verified-break -> storage.

`Application` owns all mutable session state explicitly (no module-level globals) so the
wiring stays easy to follow and debug: settings, the tray, the current SessionTracker, and
the in-progress VerifiedBreakTracker (if any) all live as attributes on one object.
"""

from __future__ import annotations

import argparse
import threading

import cv2

from breaktime.config.settings import BreakTimeSettings
from breaktime.core.logging import configure_logging, get_logger, log_event
from breaktime.core.types import (
    CalibrationProfile,
    DetectionResult,
    SessionPhase,
    TriggerReason,
)
from breaktime.debug.preview import run as run_debug_preview
from breaktime.diagnostics.crash_reporter import install as install_crash_reporter
from breaktime.notify.toast import show_break_prompt, show_break_verified
from breaktime.notify.tray import TrayApp
from breaktime.platform.autostart import set_enabled as set_autostart_enabled
from breaktime.state.session import SessionTracker
from breaktime.storage.db import record_break_event
from breaktime.vision.calibration import CalibrationSession
from breaktime.vision.capture import frames, open_camera
from breaktime.vision.detection import FaceDetector
from breaktime.vision.verified_break import VerifiedBreakTracker

_logger = get_logger("main")


class Application:
    """One running Break-Time session: the tray (main thread) plus a background thread
    driving the camera -> detection -> state -> notify loop."""

    def __init__(self, settings: BreakTimeSettings) -> None:
        self._settings = settings
        self._active_break: VerifiedBreakTracker | None = None
        self._tracker: SessionTracker | None = None
        self._tray = TrayApp(
            on_open_stats=self._open_stats,
            on_toggle_auto_start=self._toggle_auto_start,
            on_quit=self._quit,
            auto_start_enabled=settings.auto_start_enabled,
        )

    def run(self) -> None:
        install_crash_reporter(enabled=self._settings.crash_reporting_opt_in)
        if self._settings.auto_start_enabled:
            set_autostart_enabled(True)

        worker = threading.Thread(target=self._tracking_loop, daemon=True)
        worker.start()
        self._tray.run()  # blocks on the main thread until _quit() calls tray.stop()

    def _tracking_loop(self) -> None:
        with open_camera() as capture, FaceDetector() as detector:
            profile = self._calibrate(detector, capture)
            self._tracker = SessionTracker(
                continuous_time_threshold_seconds=self._settings.continuous_time_threshold_seconds,
                fatigue_blink_rate_drop_ratio=self._settings.fatigue_blink_rate_drop_ratio,
                calibration=profile,
            )

            for frame in frames(capture, self._settings.capture_fps):
                detection, _mood = detector.analyze(
                    frame, include_mood=self._settings.mood_hint_enabled
                )
                self._process(detection)

    def _calibrate(self, detector: FaceDetector, capture: cv2.VideoCapture) -> CalibrationProfile:
        session = CalibrationSession()
        log_event(_logger, "calibration_started", duration_seconds=session.duration_seconds)
        for frame in frames(capture, self._settings.capture_fps):
            detection, _ = detector.analyze(frame)
            session.observe(detection)
            if session.is_complete:
                break
        profile = session.finish()
        log_event(
            _logger,
            "calibration_complete",
            baseline_ear=profile.baseline_ear,
            baseline_blink_rate=profile.baseline_blink_rate_per_min,
        )
        return profile

    def _process(self, detection: DetectionResult) -> None:
        tracker = self._tracker
        assert tracker is not None  # set before the loop starts in _tracking_loop

        if tracker.phase in (SessionPhase.BREAK_PENDING, SessionPhase.BREAK_VERIFYING):
            self._advance_break(detection)
            return

        trigger = tracker.observe(detection)
        self._tray.update_phase(tracker.phase)
        if trigger is not None:
            self._start_break(trigger)

    def _start_break(self, trigger: TriggerReason) -> None:
        tracker = self._tracker
        assert tracker is not None

        tracker.start_break()
        self._tray.update_phase(tracker.phase)
        self._active_break = VerifiedBreakTracker(
            required_away_seconds=self._settings.verified_break_required_seconds,
            trigger_reason=trigger,
        )
        threading.Thread(target=show_break_prompt, daemon=True).start()
        log_event(_logger, "break_triggered", reason=trigger.name)

    def _advance_break(self, detection: DetectionResult) -> None:
        tracker = self._tracker
        assert tracker is not None

        if self._active_break is None:
            tracker.reset_after_break()
            return

        tracker.phase = SessionPhase.BREAK_VERIFYING
        self._tray.update_phase(tracker.phase)
        self._active_break.observe(detection)

        if self._active_break.is_verified:
            record_break_event(self._active_break.to_event())
            log_event(_logger, "break_verified")
            self._active_break = None
            tracker.reset_after_break()
            self._tray.update_phase(tracker.phase)
            threading.Thread(target=show_break_verified, daemon=True).start()

    def _open_stats(self) -> None:
        # Tray menu surface exists now; the native stats popup view is a good
        # "help wanted" issue (see docs/ROADMAP.md) rather than blocking this phase.
        log_event(_logger, "stats_requested")

    def _toggle_auto_start(self, enabled: bool) -> None:
        set_autostart_enabled(enabled)
        self._settings.auto_start_enabled = enabled
        self._settings.save()
        self._tray.set_auto_start_state(enabled)

    def _quit(self) -> None:
        log_event(_logger, "quit_requested")
        self._tray.stop()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="breaktime")
    parser.add_argument(
        "--debug-preview",
        action="store_true",
        help=(
            "Show a live local window with the camera feed and detection numbers "
            "(EAR, gaze, head pose) overlaid, for visually verifying detection is "
            "working, instead of running the normal background tray app."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    configure_logging()

    if args.debug_preview:
        run_debug_preview()
        return

    settings = BreakTimeSettings.load()
    Application(settings).run()


if __name__ == "__main__":
    main()
