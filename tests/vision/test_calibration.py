import pytest

from breaktime.core.errors import CalibrationIncompleteError
from breaktime.core.types import DetectionResult
from breaktime.vision.calibration import CalibrationSession, _Phase
from breaktime.vision.gaze import MAX_BLINK_DURATION_SECONDS

# Long durations so wall-clock time elapsing during a test run never auto-advances a
# phase -- tests drive phase transitions explicitly via `advance_phase()` instead, so
# behavior isn't coupled to how fast the test happens to execute.
_TEST_PHASES = (
    _Phase("center", "center", 3600.0),
    _Phase("top", "top", 3600.0),
    _Phase("bottom", "bottom", 3600.0),
    _Phase("left", "left", 3600.0),
    _Phase("right", "right", 3600.0),
)


def _detection(
    *,
    timestamp: float = 0.0,
    ear: float = 0.3,
    yaw: float = 0.0,
    pitch: float = 0.0,
    gaze_h: float = 0.5,
    gaze_v: float = 0.5,
    face_present: bool = True,
) -> DetectionResult:
    return DetectionResult(
        timestamp=timestamp,
        face_present=face_present,
        ear=ear if face_present else None,
        head_yaw_deg=yaw,
        head_pitch_deg=pitch,
        gaze_horizontal_ratio=gaze_h,
        gaze_vertical_ratio=gaze_v,
    )


def _feed(
    session: CalibrationSession, n: int, *, start: float = 0.0, dt: float = 0.1, **kwargs
) -> float:
    """Feeds `n` samples at increasing timestamps (never all-identical -- the blink vs.
    sustained-glance run-length logic depends on real elapsed time between samples).
    Returns the next unused timestamp, so callers can chain phases on one clock."""
    for i in range(n):
        session.observe(_detection(timestamp=start + i * dt, **kwargs))
    return start + n * dt


def test_calibration_computes_baseline_and_on_screen_ranges_from_all_phases():
    session = CalibrationSession(phases=_TEST_PHASES)

    t = 0.0
    ear_open, ear_closed = 0.3, 0.1
    for ear in [ear_open, ear_open, ear_closed, ear_open, ear_open, ear_closed]:
        t = _feed(session, 4, start=t, ear=ear, yaw=0.0, pitch=0.0, gaze_h=0.5, gaze_v=0.5)
    session.advance_phase()

    t = _feed(session, 25, start=t, yaw=0.0, pitch=-12.0, gaze_h=0.5, gaze_v=0.2)  # "top"
    session.advance_phase()
    t = _feed(session, 25, start=t, yaw=0.0, pitch=10.0, gaze_h=0.5, gaze_v=0.8)  # "bottom"
    session.advance_phase()
    t = _feed(session, 25, start=t, yaw=-18.0, pitch=0.0, gaze_h=0.25, gaze_v=0.5)  # "left"
    session.advance_phase()
    t = _feed(session, 25, start=t, yaw=16.0, pitch=0.0, gaze_h=0.75, gaze_v=0.5)  # "right"
    session.advance_phase()

    assert session.is_complete
    profile = session.finish()

    assert profile.baseline_ear == pytest.approx((ear_open * 4 + ear_closed * 2) / 6)
    assert profile.baseline_blink_rate_per_min > 0

    # Ranges must cover every phase's observed extremes (plus margin), not just center.
    assert profile.on_screen_pitch_range.contains(-12.0)
    assert profile.on_screen_pitch_range.contains(10.0)
    assert profile.on_screen_yaw_range.contains(-18.0)
    assert profile.on_screen_yaw_range.contains(16.0)
    assert profile.on_screen_gaze_vertical_range.contains(0.2)
    assert profile.on_screen_gaze_vertical_range.contains(0.8)
    assert profile.on_screen_gaze_horizontal_range.contains(0.25)
    assert profile.on_screen_gaze_horizontal_range.contains(0.75)


def test_calibration_ignores_frames_without_a_face():
    session = CalibrationSession(phases=_TEST_PHASES)
    _feed(session, 30, face_present=False)

    with pytest.raises(CalibrationIncompleteError):
        session.finish()


def test_calibration_raises_when_too_few_samples():
    session = CalibrationSession(phases=_TEST_PHASES)
    session.observe(_detection())

    with pytest.raises(CalibrationIncompleteError):
        session.finish()


def test_current_instruction_reflects_the_active_phase():
    session = CalibrationSession(phases=_TEST_PHASES)
    assert session.current_phase_name == "center"
    session.advance_phase()
    assert session.current_phase_name == "top"
    session.advance_phase()
    session.advance_phase()
    session.advance_phase()
    assert session.current_phase_name == "right"
    session.advance_phase()
    assert session.is_complete
    assert session.current_instruction == "Calibration complete"


def test_ear_samples_are_only_collected_during_the_center_phase():
    """Blink-rate baseline should reflect steady normal viewing, not deliberately
    fixating at a screen edge (which can suppress natural blinking)."""
    session = CalibrationSession(phases=_TEST_PHASES)
    t = _feed(session, 25, ear=0.3)
    session.advance_phase()
    t = _feed(session, 25, start=t, ear=0.05, pitch=-12.0, gaze_v=0.2)  # would tank it if counted
    session.advance_phase()
    t = _feed(session, 25, start=t, pitch=10.0, gaze_v=0.8)
    session.advance_phase()
    t = _feed(session, 25, start=t, yaw=-18.0, gaze_h=0.25)
    session.advance_phase()
    _feed(session, 25, start=t, yaw=16.0, gaze_h=0.75)
    session.advance_phase()

    profile = session.finish()
    assert profile.baseline_ear == pytest.approx(0.3)


def test_brief_low_ear_run_is_excluded_from_ranges_as_a_blink():
    """A short low-EAR run (a real blink) must not corrupt the calibrated range with
    whatever pose/gaze values happened to occur during it."""
    session = CalibrationSession(phases=_TEST_PHASES)
    t = _feed(session, 25, ear=0.3, pitch=0.0)
    session.advance_phase()
    # A brief blink (well under MAX_BLINK_DURATION_SECONDS) at an extreme, otherwise-
    # unseen pitch value.
    dt = MAX_BLINK_DURATION_SECONDS / 10
    _feed(session, 3, start=t, dt=dt, ear=0.02, pitch=-80.0)
    for _ in range(4):
        session.advance_phase()

    profile = session.finish()
    assert not profile.on_screen_pitch_range.contains(-80.0)


def test_sustained_low_ear_run_is_kept_as_a_genuine_gaze_signal():
    """The fix for the bug found live: a hard glance can lower EAR for its whole
    duration, not just blink-length -- that must still contribute to the calibrated
    range, not be silently discarded as if it were a blink."""
    session = CalibrationSession(phases=_TEST_PHASES)
    t = _feed(session, 25, ear=0.3, pitch=0.0)
    session.advance_phase()
    # Sustained low EAR (well over MAX_BLINK_DURATION_SECONDS) at a specific pitch --
    # e.g. a hard glance toward the screen's top edge that also lowers apparent EAR.
    dt = (MAX_BLINK_DURATION_SECONDS * 3) / 20
    _feed(session, 20, start=t, dt=dt, ear=0.02, pitch=-14.0)
    for _ in range(4):
        session.advance_phase()

    profile = session.finish()
    assert profile.on_screen_pitch_range.contains(-14.0)
