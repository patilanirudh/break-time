from breaktime.core.types import CalibrationProfile, DetectionResult, GazeRange, TriggerReason
from breaktime.vision.verified_break import VerifiedBreakTracker


def _profile() -> CalibrationProfile:
    return CalibrationProfile(
        baseline_ear=0.25,
        baseline_blink_rate_per_min=15.0,
        blink_ear_threshold=0.19,
        on_screen_yaw_range=GazeRange(minimum=-15.0, maximum=15.0),
        on_screen_pitch_range=GazeRange(minimum=-15.0, maximum=15.0),
        on_screen_gaze_horizontal_range=GazeRange(minimum=0.35, maximum=0.65),
        on_screen_gaze_vertical_range=GazeRange(minimum=0.35, maximum=0.65),
        calibrated_at=0.0,
    )


def _detection(
    *,
    face_present: bool,
    on_screen: bool | None,
    timestamp: float,
) -> DetectionResult:
    # on_screen=None means "can't tell" (used for the face-absent case below); when it's
    # True/False we just pick head-pose values that are trivially within/outside the
    # profile's baseline +/- the gaze module's tolerance, since is_looking_at_screen()
    # requires *all* signals (yaw, pitch, gaze h/v) to agree.
    deg = 0.0 if on_screen else 90.0
    ratio = 0.5 if on_screen else 0.95
    return DetectionResult(
        timestamp=timestamp,
        face_present=face_present,
        ear=None,
        head_yaw_deg=deg,
        head_pitch_deg=deg,
        gaze_horizontal_ratio=ratio,
        gaze_vertical_ratio=ratio,
    )


def test_break_not_verified_while_still_looking_at_screen():
    tracker = VerifiedBreakTracker(
        required_away_seconds=20.0,
        trigger_reason=TriggerReason.TIME_THRESHOLD,
        calibration=_profile(),
    )
    tracker.observe(_detection(face_present=True, on_screen=True, timestamp=0.0))
    assert not tracker.is_verified


def test_break_verified_after_looking_away_long_enough():
    tracker = VerifiedBreakTracker(
        required_away_seconds=20.0,
        trigger_reason=TriggerReason.FATIGUE,
        calibration=_profile(),
    )
    tracker.observe(_detection(face_present=True, on_screen=False, timestamp=0.0))
    tracker.observe(_detection(face_present=True, on_screen=False, timestamp=10.0))
    assert not tracker.is_verified

    tracker.observe(_detection(face_present=True, on_screen=False, timestamp=21.0))
    assert tracker.is_verified

    event = tracker.to_event()
    assert event.verified is True
    assert event.trigger_reason is TriggerReason.FATIGUE


def test_looking_back_at_screen_resets_the_away_timer():
    tracker = VerifiedBreakTracker(
        required_away_seconds=20.0,
        trigger_reason=TriggerReason.TIME_THRESHOLD,
        calibration=_profile(),
    )
    tracker.observe(_detection(face_present=True, on_screen=False, timestamp=0.0))
    tracker.observe(_detection(face_present=True, on_screen=True, timestamp=5.0))
    tracker.observe(_detection(face_present=True, on_screen=False, timestamp=15.0))
    assert not tracker.is_verified

    tracker.observe(_detection(face_present=True, on_screen=False, timestamp=36.0))
    assert tracker.is_verified


def test_a_blink_mid_away_streak_does_not_reset_it():
    """Regression test for a real bug found via live testing: an unreadable frame (e.g.
    mid-blink, ear below the personal blink threshold) was being treated as "confirmed
    still on screen," silently resetting genuine away streaks on every blink."""
    profile = _profile()
    tracker = VerifiedBreakTracker(
        required_away_seconds=20.0,
        trigger_reason=TriggerReason.TIME_THRESHOLD,
        calibration=profile,
    )
    tracker.observe(_detection(face_present=True, on_screen=False, timestamp=0.0))

    blink_frame = DetectionResult(
        timestamp=10.0,
        face_present=True,
        ear=profile.blink_ear_threshold - 0.05,  # below threshold -> mid-blink
        head_yaw_deg=90.0,  # otherwise clearly "away" head pose
        head_pitch_deg=90.0,
        gaze_horizontal_ratio=0.95,
        gaze_vertical_ratio=0.95,
    )
    tracker.observe(blink_frame)
    assert not tracker.is_verified  # blink must not have completed it early either

    tracker.observe(_detection(face_present=True, on_screen=False, timestamp=21.0))
    assert tracker.is_verified  # the streak survived the blink frame uninterrupted


def test_stepping_away_entirely_counts_as_a_break():
    tracker = VerifiedBreakTracker(
        required_away_seconds=20.0,
        trigger_reason=TriggerReason.TIME_THRESHOLD,
        calibration=_profile(),
    )
    tracker.observe(
        DetectionResult(
            timestamp=0.0,
            face_present=False,
            ear=None,
            head_yaw_deg=None,
            head_pitch_deg=None,
            gaze_horizontal_ratio=None,
            gaze_vertical_ratio=None,
        )
    )
    tracker.observe(
        DetectionResult(
            timestamp=21.0,
            face_present=False,
            ear=None,
            head_yaw_deg=None,
            head_pitch_deg=None,
            gaze_horizontal_ratio=None,
            gaze_vertical_ratio=None,
        )
    )
    assert tracker.is_verified
