from breaktime.core.types import DetectionResult, TriggerReason
from breaktime.vision.verified_break import VerifiedBreakTracker


def _detection(
    *, face_present: bool, gaze_on_screen: bool | None, timestamp: float
) -> DetectionResult:
    return DetectionResult(
        timestamp=timestamp,
        face_present=face_present,
        ear=None,
        gaze_on_screen=gaze_on_screen,
        head_yaw_deg=None,
        head_pitch_deg=None,
    )


def test_break_not_verified_while_still_looking_at_screen():
    tracker = VerifiedBreakTracker(
        required_away_seconds=20.0, trigger_reason=TriggerReason.TIME_THRESHOLD
    )
    tracker.observe(_detection(face_present=True, gaze_on_screen=True, timestamp=0.0))
    assert not tracker.is_verified


def test_break_verified_after_looking_away_long_enough():
    tracker = VerifiedBreakTracker(required_away_seconds=20.0, trigger_reason=TriggerReason.FATIGUE)
    tracker.observe(_detection(face_present=True, gaze_on_screen=False, timestamp=0.0))
    tracker.observe(_detection(face_present=True, gaze_on_screen=False, timestamp=10.0))
    assert not tracker.is_verified

    tracker.observe(_detection(face_present=True, gaze_on_screen=False, timestamp=21.0))
    assert tracker.is_verified

    event = tracker.to_event()
    assert event.verified is True
    assert event.trigger_reason is TriggerReason.FATIGUE


def test_looking_back_at_screen_resets_the_away_timer():
    tracker = VerifiedBreakTracker(
        required_away_seconds=20.0, trigger_reason=TriggerReason.TIME_THRESHOLD
    )
    tracker.observe(_detection(face_present=True, gaze_on_screen=False, timestamp=0.0))
    tracker.observe(_detection(face_present=True, gaze_on_screen=True, timestamp=5.0))
    tracker.observe(_detection(face_present=True, gaze_on_screen=False, timestamp=15.0))
    assert not tracker.is_verified

    tracker.observe(_detection(face_present=True, gaze_on_screen=False, timestamp=36.0))
    assert tracker.is_verified


def test_stepping_away_entirely_counts_as_a_break():
    tracker = VerifiedBreakTracker(
        required_away_seconds=20.0, trigger_reason=TriggerReason.TIME_THRESHOLD
    )
    tracker.observe(_detection(face_present=False, gaze_on_screen=None, timestamp=0.0))
    tracker.observe(_detection(face_present=False, gaze_on_screen=None, timestamp=21.0))
    assert tracker.is_verified
