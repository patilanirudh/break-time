from breaktime.core.types import CalibrationProfile, DetectionResult, GazeRange, TriggerReason
from breaktime.state.session import SessionTracker


def _profile(baseline_blink_rate: float = 15.0) -> CalibrationProfile:
    return CalibrationProfile(
        baseline_ear=0.3,
        baseline_blink_rate_per_min=baseline_blink_rate,
        blink_ear_threshold=0.21,  # between the tests' ear=0.1 (closed) and ear=0.3 (open)
        on_screen_yaw_range=GazeRange(minimum=-15.0, maximum=15.0),
        on_screen_pitch_range=GazeRange(minimum=-15.0, maximum=15.0),
        on_screen_gaze_horizontal_range=GazeRange(minimum=0.35, maximum=0.65),
        on_screen_gaze_vertical_range=GazeRange(minimum=0.35, maximum=0.65),
        calibrated_at=0.0,
    )


def _detection(timestamp: float, *, face_present: bool = True, ear: float = 0.3) -> DetectionResult:
    return DetectionResult(
        timestamp=timestamp,
        face_present=face_present,
        ear=ear if face_present else None,
        head_yaw_deg=0.0,
        head_pitch_deg=0.0,
        gaze_horizontal_ratio=0.5,
        gaze_vertical_ratio=0.5,
    )


def test_triggers_on_continuous_time_threshold():
    tracker = SessionTracker(
        continuous_time_threshold_seconds=60.0,
        fatigue_blink_rate_drop_ratio=0.9,  # lenient enough not to fire on its own
        calibration=_profile(),
    )
    trigger = None
    for t in range(0, 61, 5):
        trigger = tracker.observe(_detection(float(t)))
    assert trigger is TriggerReason.TIME_THRESHOLD


def test_does_not_trigger_before_threshold():
    tracker = SessionTracker(
        continuous_time_threshold_seconds=60.0,
        fatigue_blink_rate_drop_ratio=0.9,
        calibration=_profile(),
    )
    trigger = None
    for t in range(0, 30, 5):
        trigger = tracker.observe(_detection(float(t)))
    assert trigger is None


def test_stepping_away_resets_continuous_time():
    tracker = SessionTracker(
        continuous_time_threshold_seconds=60.0,
        fatigue_blink_rate_drop_ratio=0.9,
        calibration=_profile(),
    )
    for t in range(0, 40, 5):
        tracker.observe(_detection(float(t)))

    tracker.observe(_detection(41.0, face_present=False))
    tracker.observe(_detection(47.0, face_present=False))  # >5s away -> resets

    trigger = tracker.observe(_detection(48.0))
    assert trigger is None

    trigger = tracker.observe(_detection(70.0))  # only 22s since the restart
    assert trigger is None


def test_triggers_on_fatigue_when_blink_rate_drops():
    tracker = SessionTracker(
        continuous_time_threshold_seconds=100_000.0,  # effectively disabled
        fatigue_blink_rate_drop_ratio=0.5,
        calibration=_profile(baseline_blink_rate=20.0),  # needs >=10/min to avoid fatigue
    )
    blink_seconds = {10, 40}  # only 2 blinks across the 60s window, well under threshold
    trigger = None
    for t in range(0, 66):
        ear = 0.1 if t in blink_seconds else 0.3
        trigger = tracker.observe(_detection(float(t), ear=ear))
    assert trigger is TriggerReason.FATIGUE
