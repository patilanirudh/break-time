import pytest

from breaktime.core.errors import CalibrationIncompleteError
from breaktime.core.types import DetectionResult
from breaktime.vision.calibration import CalibrationSession


def _detection(ear: float, timestamp: float, *, face_present: bool = True) -> DetectionResult:
    return DetectionResult(
        timestamp=timestamp,
        face_present=face_present,
        ear=ear if face_present else None,
        gaze_on_screen=True,
        head_yaw_deg=0.0,
        head_pitch_deg=0.0,
    )


def test_calibration_computes_baseline_ear_and_blink_rate():
    session = CalibrationSession(duration_seconds=0.0)
    ear_open, ear_closed = 0.3, 0.1
    timestamps = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    ears = [ear_open, ear_open, ear_closed, ear_open, ear_open, ear_closed]
    for t, ear in zip(timestamps, ears, strict=True):
        for _ in range(4):  # pad past the minimum sample count
            session.observe(_detection(ear, t))

    profile = session.finish()
    assert profile.baseline_ear == pytest.approx(sum(ears) / len(ears))
    assert profile.baseline_blink_rate_per_min > 0


def test_calibration_ignores_frames_without_a_face():
    session = CalibrationSession(duration_seconds=0.0)
    for t in range(30):
        session.observe(_detection(0.3, float(t), face_present=False))

    with pytest.raises(CalibrationIncompleteError):
        session.finish()


def test_calibration_raises_when_too_few_samples():
    session = CalibrationSession(duration_seconds=0.0)
    session.observe(_detection(0.3, 0.0))

    with pytest.raises(CalibrationIncompleteError):
        session.finish()
