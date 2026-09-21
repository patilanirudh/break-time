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
    """Output of one vision analysis pass over a single (immediately discarded) frame."""

    timestamp: float
    face_present: bool
    ear: float | None
    gaze_on_screen: bool | None
    head_yaw_deg: float | None
    head_pitch_deg: float | None


@dataclass(frozen=True, slots=True)
class CalibrationProfile:
    """A user's personalized baseline, captured once during first-run calibration.

    `blink_ear_threshold` is derived from this user's own open-eye EAR (a ratio, not a
    fixed constant) -- absolute EAR magnitude varies meaningfully across people, cameras,
    and lighting, so a single hardcoded threshold is not reliable across users.
    """

    baseline_ear: float
    baseline_blink_rate_per_min: float
    blink_ear_threshold: float
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
