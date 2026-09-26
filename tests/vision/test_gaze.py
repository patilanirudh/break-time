from breaktime.core.types import CalibrationProfile, DetectionResult, GazeRange
from breaktime.vision.gaze import MAX_BLINK_DURATION_SECONDS, GazeMonitor


def _profile() -> CalibrationProfile:
    return CalibrationProfile(
        baseline_ear=0.25,
        baseline_blink_rate_per_min=15.0,
        blink_ear_threshold=0.19,
        on_screen_yaw_range=GazeRange(minimum=-20.0, maximum=15.0),
        on_screen_pitch_range=GazeRange(minimum=-15.0, maximum=10.0),
        on_screen_gaze_horizontal_range=GazeRange(minimum=0.35, maximum=0.68),
        on_screen_gaze_vertical_range=GazeRange(minimum=0.15, maximum=0.55),
        calibrated_at=0.0,
    )


def _detection(
    *,
    timestamp: float = 0.0,
    yaw: float,
    pitch: float,
    gaze_h: float,
    gaze_v: float,
    face_present: bool = True,
    ear: float | None = None,
) -> DetectionResult:
    return DetectionResult(
        timestamp=timestamp,
        face_present=face_present,
        ear=ear,
        head_yaw_deg=yaw,
        head_pitch_deg=pitch,
        gaze_horizontal_ratio=gaze_h,
        gaze_vertical_ratio=gaze_v,
    )


def test_returns_none_when_no_face():
    monitor = GazeMonitor(_profile())
    detection = _detection(yaw=0, pitch=0, gaze_h=0.5, gaze_v=0.5, face_present=False)
    assert monitor.judge(detection) is None


def test_center_of_calibrated_range_counts_as_on_screen():
    monitor = GazeMonitor(_profile())
    detection = _detection(yaw=-2.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35)
    assert monitor.judge(detection) is True


def test_within_calibrated_screen_edge_range_counts_as_on_screen():
    """The whole point of calibrating against real screen edges: a look at the
    screen's own top/bottom/left/right edge, captured during calibration, must not be
    misread as "looking away"."""
    profile = _profile()
    on_left = _detection(yaw=-20.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35)
    on_right = _detection(yaw=15.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35)
    on_top = _detection(yaw=-2.0, pitch=-15.0, gaze_h=0.5, gaze_v=0.35)
    on_bottom = _detection(yaw=-2.0, pitch=10.0, gaze_h=0.5, gaze_v=0.35)
    assert GazeMonitor(profile).judge(on_left) is True
    assert GazeMonitor(profile).judge(on_right) is True
    assert GazeMonitor(profile).judge(on_top) is True
    assert GazeMonitor(profile).judge(on_bottom) is True


def test_beyond_calibrated_range_is_looking_away():
    monitor = GazeMonitor(_profile())
    # well past both the pitch and gaze_v calibrated maximums
    detection = _detection(yaw=-2.0, pitch=25.0, gaze_h=0.5, gaze_v=0.9)
    assert monitor.judge(detection) is False


def test_large_head_turn_is_detected_as_away():
    monitor = GazeMonitor(_profile())
    detection = _detection(yaw=40.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35)
    assert monitor.judge(detection) is False


def test_a_brief_blink_returns_none_and_does_not_confirm_on_screen():
    """Regression test: live testing found blink frames produce corrupted eye-in-socket
    readings (an observed live value of -0.04, well outside any real range) that would
    otherwise be misread as a large, spurious "looking away." A brief low-EAR reading
    must return None (unknown), not True or False."""
    profile = _profile()
    monitor = GazeMonitor(profile)
    blink_frame = _detection(
        timestamp=10.0,
        yaw=-2.0,
        pitch=-2.0,
        gaze_h=0.5,
        gaze_v=-0.04,  # corrupted mid-blink reading, well outside the calibrated range
        ear=profile.blink_ear_threshold - 0.02,
    )
    assert monitor.judge(blink_frame) is None


def test_sustained_low_ear_is_not_treated_as_a_blink():
    """The fix for the residual bug found live: a hard eyes-only glance at an extreme
    angle can also lower EAR (eyelid shape changes with gaze angle) and *sustain* the
    low reading for the whole glance -- seconds, not a blink's ~100-400ms. Once a
    low-EAR run has lasted longer than a real blink could, judgment must resume using
    the actual gaze/pose signals instead of returning None forever."""
    profile = _profile()
    monitor = GazeMonitor(profile)
    low_ear = profile.blink_ear_threshold - 0.02

    # First frame of the low-EAR run: still within blink duration -- unknown.
    first = _detection(timestamp=0.0, yaw=-2.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35, ear=low_ear)
    assert monitor.judge(first) is None

    # Well past MAX_BLINK_DURATION_SECONDS, EAR still low, but gaze is clearly away.
    later_timestamp = MAX_BLINK_DURATION_SECONDS + 0.5
    sustained_away = _detection(
        timestamp=later_timestamp, yaw=-2.0, pitch=30.0, gaze_h=0.5, gaze_v=0.35, ear=low_ear
    )
    assert monitor.judge(sustained_away) is False


def test_blink_state_resets_once_ear_recovers():
    profile = _profile()
    monitor = GazeMonitor(profile)
    low_ear = profile.blink_ear_threshold - 0.02
    normal_ear = profile.blink_ear_threshold + 0.1

    first = _detection(timestamp=0.0, yaw=-2.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35, ear=low_ear)
    monitor.judge(first)
    # Recovers quickly -- a real blink -- before sustained-duration judgment kicks in.
    monitor.judge(
        _detection(timestamp=0.1, yaw=-2.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35, ear=normal_ear)
    )
    # A second low-EAR frame long after the first must be judged as a *new* run, not
    # inherit the first run's elapsed time.
    result = monitor.judge(
        _detection(timestamp=0.2, yaw=-2.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35, ear=low_ear)
    )
    assert result is None
