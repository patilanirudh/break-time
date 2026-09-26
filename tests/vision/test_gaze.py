from breaktime.core.types import CalibrationProfile, DetectionResult, GazeRange
from breaktime.vision.gaze import is_looking_at_screen


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
    yaw: float,
    pitch: float,
    gaze_h: float,
    gaze_v: float,
    face_present: bool = True,
    ear: float | None = None,
) -> DetectionResult:
    return DetectionResult(
        timestamp=0.0,
        face_present=face_present,
        ear=ear,
        head_yaw_deg=yaw,
        head_pitch_deg=pitch,
        gaze_horizontal_ratio=gaze_h,
        gaze_vertical_ratio=gaze_v,
    )


def test_returns_none_when_no_face():
    detection = _detection(yaw=0, pitch=0, gaze_h=0.5, gaze_v=0.5, face_present=False)
    assert is_looking_at_screen(detection, _profile()) is None


def test_center_of_calibrated_range_counts_as_on_screen():
    profile = _profile()
    detection = _detection(yaw=-2.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35)
    assert is_looking_at_screen(detection, profile) is True


def test_within_calibrated_screen_edge_range_counts_as_on_screen():
    """The whole point of calibrating against real screen edges: a look at the
    screen's own top/bottom/left/right edge, captured during calibration, must not be
    misread as "looking away"."""
    profile = _profile()
    # right at the calibrated edges
    on_left = _detection(yaw=-20.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35)
    on_right = _detection(yaw=15.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35)
    on_top = _detection(yaw=-2.0, pitch=-15.0, gaze_h=0.5, gaze_v=0.35)
    on_bottom = _detection(yaw=-2.0, pitch=10.0, gaze_h=0.5, gaze_v=0.35)
    assert is_looking_at_screen(on_left, profile) is True
    assert is_looking_at_screen(on_right, profile) is True
    assert is_looking_at_screen(on_top, profile) is True
    assert is_looking_at_screen(on_bottom, profile) is True


def test_beyond_calibrated_range_is_looking_away():
    profile = _profile()
    # well past both the pitch and gaze_v calibrated maximums
    detection = _detection(yaw=-2.0, pitch=25.0, gaze_h=0.5, gaze_v=0.9)
    assert is_looking_at_screen(detection, profile) is False


def test_returns_none_during_a_blink_regardless_of_other_signals():
    """Regression test: live testing found blink frames produce corrupted eye-in-socket
    readings (an observed live value of -0.04, well outside any real range) that would
    otherwise be misread as a large, spurious "looking away."""
    profile = _profile()
    detection = _detection(
        yaw=-2.0,
        pitch=-2.0,
        gaze_h=0.5,
        gaze_v=-0.04,  # corrupted mid-blink reading, well outside the calibrated range
        ear=profile.blink_ear_threshold - 0.02,  # below this user's blink threshold
    )
    assert is_looking_at_screen(detection, profile) is None


def test_large_head_turn_is_detected_as_away():
    profile = _profile()
    detection = _detection(yaw=40.0, pitch=-2.0, gaze_h=0.5, gaze_v=0.35)
    assert is_looking_at_screen(detection, profile) is False
