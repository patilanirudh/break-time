"""Shared, typed data structures passed between Break-Time's pipeline stages.

Every pipeline stage (vision -> state -> notify -> storage) communicates exclusively
through these frozen dataclasses. Keeping the interfaces typed and explicit is what makes
each stage independently testable with synthetic data, with no real camera required.

None of these types ever carry raw image/frame data -- only derived numeric or boolean
signals. That is a deliberate privacy boundary, not an oversight.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TriggerReason(Enum):
    """Why a break was triggered."""

    TIME_THRESHOLD = auto()
    FATIGUE = auto()


class SessionPhase(Enum):
    """Current phase of the continuous-tracking state machine."""

    ACTIVE = auto()
    AWAY = auto()
    BREAK_PENDING = auto()
    BREAK_VERIFYING = auto()
    BREAK_COMPLETE = auto()


@dataclass(frozen=True, slots=True)
class DetectionResult:
    """Output of one vision analysis pass over a single (immediately discarded) frame.

    `gaze_horizontal_ratio` / `gaze_vertical_ratio` are raw eye-in-socket signals (iris
    center position relative to the eye corners, ~0.5 when centered) -- deliberately raw,
    not a precomputed "on screen" boolean, because judging that requires comparing against
    a user's own calibrated baseline (see vision/gaze.py). Head pose alone (yaw/pitch)
    cannot tell "looking at the keyboard" or "eyes moved, head didn't" apart from "looking
    at the screen" -- that's what the gaze ratios add.
    """

    timestamp: float
    face_present: bool
    ear: float | None
    head_yaw_deg: float | None
    head_pitch_deg: float | None
    gaze_horizontal_ratio: float | None
    gaze_vertical_ratio: float | None


@dataclass(frozen=True, slots=True)
class GazeRange:
    """An observed min/max span for one signal across all "genuinely on-screen" looks
    recorded during calibration (center plus each screen edge), with a small margin
    already folded in to absorb ordinary frame-to-frame noise.

    This replaces an earlier single-center-point-plus-fixed-tolerance design: live
    testing showed a symmetric tolerance around one center reading can't tell a glance
    at the screen's own edge apart from a glance just beyond it (e.g. down at a
    keyboard), because both may be a similar angular distance from center. Calibrating
    against the actual screen edges directly grounds "on screen" in what the screen
    itself covers for this user's camera and seating position, not a guessed number.
    """

    minimum: float
    maximum: float

    def contains(self, value: float) -> bool:
        return self.minimum <= value <= self.maximum


@dataclass(frozen=True, slots=True)
class CalibrationProfile:
    """A user's personalized baseline, captured once during first-run calibration.

    Every threshold here is derived from this user's own measurements, not a fixed
    constant -- absolute EAR, head pose, and eye position all vary meaningfully across
    people, camera placement, and lighting, so one hardcoded number is not reliable
    across users (confirmed live: a fixed blink threshold and a fixed head-angle gaze
    threshold both produced wrong results for real users/webcam setups).
    """

    baseline_ear: float
    baseline_blink_rate_per_min: float
    blink_ear_threshold: float
    on_screen_yaw_range: GazeRange
    on_screen_pitch_range: GazeRange
    on_screen_gaze_horizontal_range: GazeRange
    on_screen_gaze_vertical_range: GazeRange
    calibrated_at: float


@dataclass(frozen=True, slots=True)
class FatigueSignal:
    """Whether current blink rate indicates fatigue relative to the user's baseline."""

    is_fatigued: bool
    current_blink_rate_per_min: float
    baseline_blink_rate_per_min: float


@dataclass(frozen=True, slots=True)
class BreakEvent:
    """A single break, from trigger to (optionally) verified completion."""

    trigger_reason: TriggerReason
    started_at: float
    completed_at: float | None
    verified: bool


@dataclass(frozen=True, slots=True)
class MoodSignal:
    """Experimental, non-diagnostic facial-tension hint. See mood/signal.py for caveats."""

    timestamp: float
    tension_score: float | None
