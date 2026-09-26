"""First-run baseline calibration.

Captures the user's own normal EAR (eye aspect ratio), blink rate, and -- across a short
sequence of "look at the center, then each screen edge" phases -- the actual observed
range of head pose and eye-in-socket position for genuinely on-screen looks. Operates
purely on the DetectionResult stream -- it has no camera access of its own, which is what
makes it testable with synthetic data (see tests/vision/test_calibration.py).

Three things confirmed live, not hypothetically, that shaped this design:
- Blink detection needs an EAR threshold below which the eye counts as "closed." A real
  user's open-eye EAR baseline (~0.196) landed *below* a plausible-looking fixed
  threshold (0.21), because absolute EAR magnitude depends on camera, lighting, and
  landmark geometry, not just eye state.
- A single "look at the screen normally" center point plus a guessed symmetric
  tolerance was not enough to reliably separate "looking at the screen's own edge" from
  "looking just beyond it" (e.g. down at a keyboard) -- both can be a similar angular
  distance from center. Calibrating against the screen's actual edges grounds the
  on-screen range in this user's real screen/seating geometry instead.
- A single frame's eye-in-socket ratio is unreliable during a blink, producing outlier
  readings (observed live: a vertical ratio of -0.21 -- outside any physically
  meaningful range). Because the on-screen range is a min/max, not an average, even one
  such outlier permanently and silently widens "on screen" to include nonsense values --
  far more damaging here than it would be to a mean. So blink frames are identified and
  excluded *before* computing ranges, not just at judgment time (see vision/gaze.py).
  Excluding *every* low-EAR frame this way was itself found live to be too broad: a hard
  eyes-only glance can also lower EAR (eyelid shape changes with gaze angle) and *sustain*
  it for the whole glance, not just a blink's ~100-400ms. Only a brief low-EAR run is
  treated as a blink and dropped; a sustained one is kept, using the same duration-based
  rule as live judgment (vision/gaze.py's `MAX_BLINK_DURATION_SECONDS`).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from breaktime.core.errors import CalibrationIncompleteError
from breaktime.core.types import CalibrationProfile, DetectionResult, GazeRange
from breaktime.vision.gaze import MAX_BLINK_DURATION_SECONDS

_MIN_VALID_SAMPLES = 20
_BLINK_THRESHOLD_RATIO = 0.75
_GAZE_RANGE_MARGIN = 0.05
_ANGLE_RANGE_MARGIN_DEG = 5.0


@dataclass(frozen=True, slots=True)
class _Phase:
    name: str
    instruction: str
    duration_seconds: float


_DEFAULT_PHASES: tuple[_Phase, ...] = (
    _Phase("center", "Look at your screen and work normally", 90.0),
    _Phase("top", "Look at the TOP edge of your screen", 8.0),
    _Phase("bottom", "Look at the BOTTOM edge of your screen", 8.0),
    _Phase("left", "Look at the LEFT edge of your screen", 8.0),
    _Phase("right", "Look at the RIGHT edge of your screen", 8.0),
)


@dataclass(frozen=True, slots=True)
class _Sample:
    """One frame's worth of raw signals, kept together so blink exclusion (which needs
    `ear` and `timestamp`) can be applied consistently to the pose/gaze values from that
    same frame."""

    phase: str
    timestamp: float
    ear: float | None
    yaw: float | None
    pitch: float | None
    gaze_h: float | None
    gaze_v: float | None


@dataclass
class CalibrationSession:
    """Feed DetectionResults in via `observe`; call `finish` once `is_complete`.

    Advances through `phases` automatically based on elapsed time -- callers don't drive
    phase transitions themselves, but can read `current_instruction` each frame to show
    the user what to do right now (see debug/preview.py, main.py).
    """

    phases: tuple[_Phase, ...] = _DEFAULT_PHASES
    _phase_index: int = 0
    _phase_started_at: float = field(default_factory=time.monotonic)
    _samples: list[_Sample] = field(default_factory=list)

    @property
    def current_phase_name(self) -> str:
        if self.is_complete:
            return self.phases[-1].name
        return self.phases[self._phase_index].name

    @property
    def current_instruction(self) -> str:
        if self.is_complete:
            return "Calibration complete"
        return self.phases[self._phase_index].instruction

    @property
    def current_phase_remaining_seconds(self) -> float:
        if self.is_complete:
            return 0.0
        phase = self.phases[self._phase_index]
        return max(0.0, phase.duration_seconds - (time.monotonic() - self._phase_started_at))

    @property
    def is_complete(self) -> bool:
        return self._phase_index >= len(self.phases)

    def observe(self, result: DetectionResult) -> None:
        if self.is_complete:
            return

        if result.face_present:
            self._samples.append(
                _Sample(
                    phase=self.current_phase_name,
                    timestamp=result.timestamp,
                    ear=result.ear,
                    yaw=result.head_yaw_deg,
                    pitch=result.head_pitch_deg,
                    gaze_h=result.gaze_horizontal_ratio,
                    gaze_v=result.gaze_vertical_ratio,
                )
            )

        if self.current_phase_remaining_seconds <= 0.0:
            self._phase_index += 1
            self._phase_started_at = time.monotonic()

    def advance_phase(self) -> None:
        """Force-advance to the next phase immediately, bypassing the elapsed-time
        check. Only meant for tests -- production code always advances via elapsed
        wall-clock time, so behavior isn't coupled to test execution speed."""
        self._phase_index += 1
        self._phase_started_at = time.monotonic()

    def finish(self) -> CalibrationProfile:
        center_ear = [s.ear for s in self._samples if s.phase == "center" and s.ear is not None]
        all_yaw = [s.yaw for s in self._samples if s.yaw is not None]

        if len(center_ear) < _MIN_VALID_SAMPLES or len(all_yaw) < _MIN_VALID_SAMPLES:
            raise CalibrationIncompleteError(
                detail=f"only {len(center_ear)} EAR / {len(all_yaw)} pose samples collected"
            )

        baseline_ear = _mean(center_ear)
        blink_ear_threshold = baseline_ear * _BLINK_THRESHOLD_RATIO
        blink_count = _count_blinks(center_ear, blink_ear_threshold)
        minutes = max(self.phases[0].duration_seconds / 60.0, 1e-6)
        baseline_blink_rate = blink_count / minutes

        # Blink frames produce unreliable eye/pose readings (see module docstring) --
        # exclude them from the on-screen range, not just from live judgment, since a
        # min/max range is far more sensitive to a single outlier than an average is.
        # Only a *brief* low-EAR run is a blink; a sustained one is a real gaze signal
        # (see module docstring) and must be kept, not discarded.
        awake = _exclude_transient_blinks(self._samples, blink_ear_threshold)

        return CalibrationProfile(
            baseline_ear=baseline_ear,
            baseline_blink_rate_per_min=baseline_blink_rate,
            blink_ear_threshold=blink_ear_threshold,
            on_screen_yaw_range=_range_with_margin(
                [s.yaw for s in awake if s.yaw is not None], _ANGLE_RANGE_MARGIN_DEG
            ),
            on_screen_pitch_range=_range_with_margin(
                [s.pitch for s in awake if s.pitch is not None], _ANGLE_RANGE_MARGIN_DEG
            ),
            on_screen_gaze_horizontal_range=_range_with_margin(
                [s.gaze_h for s in awake if s.gaze_h is not None], _GAZE_RANGE_MARGIN
            ),
            on_screen_gaze_vertical_range=_range_with_margin(
                [s.gaze_v for s in awake if s.gaze_v is not None], _GAZE_RANGE_MARGIN
            ),
            calibrated_at=time.time(),
        )


def _mean(samples: list[float]) -> float:
    return sum(samples) / len(samples)


def _range_with_margin(samples: list[float], margin: float) -> GazeRange:
    if not samples:
        return GazeRange(minimum=-margin, maximum=margin)
    return GazeRange(minimum=min(samples) - margin, maximum=max(samples) + margin)


def _exclude_transient_blinks(samples: list[_Sample], threshold: float) -> list[_Sample]:
    """Drop samples that are part of a brief (<= MAX_BLINK_DURATION_SECONDS) low-EAR
    run -- a real blink -- while keeping samples from a longer, sustained low-EAR run,
    which is a genuine gaze signal, not a blink (see module docstring)."""
    kept: list[_Sample] = []
    pending_run: list[_Sample] = []

    def flush_run() -> None:
        if not pending_run:
            return
        duration = pending_run[-1].timestamp - pending_run[0].timestamp
        if duration > MAX_BLINK_DURATION_SECONDS:
            kept.extend(pending_run)
        pending_run.clear()

    for sample in samples:
        is_low_ear = sample.ear is not None and sample.ear < threshold
        if is_low_ear:
            pending_run.append(sample)
        else:
            flush_run()
            kept.append(sample)
    flush_run()
    return kept


def _count_blinks(ear_samples: list[float], threshold: float) -> int:
    """Count open->closed transitions in an ordered EAR sample sequence."""
    count = 0
    was_open = True
    for ear in ear_samples:
        is_open = ear >= threshold
        if was_open and not is_open:
            count += 1
        was_open = is_open
    return count
