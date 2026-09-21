"""First-run baseline calibration.

Captures the user's own normal EAR (eye aspect ratio) and blink rate over a short window
so fatigue thresholds are personalized instead of one hardcoded number for every user.
Operates purely on the DetectionResult stream -- it has no camera access of its own,
which is what makes it testable with synthetic data (see tests/vision/test_calibration.py).

Blink detection needs an EAR threshold below which the eye counts as "closed." A single
fixed absolute value does not generalize well: live testing showed a real user's open-eye
EAR baseline (~0.196) can land *below* a plausible-looking fixed threshold (0.21),
because absolute EAR magnitude depends on camera, lighting, and landmark geometry, not
just eye state. So the threshold is derived as a ratio of this user's own measured
baseline EAR instead of a constant.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from breaktime.core.errors import CalibrationIncompleteError
from breaktime.core.types import CalibrationProfile, DetectionResult

DEFAULT_CALIBRATION_DURATION_SECONDS = 120.0
_MIN_VALID_SAMPLES = 20
_BLINK_THRESHOLD_RATIO = 0.75


@dataclass
class CalibrationSession:
    """Feed DetectionResults in via `observe`; call `finish` once `is_complete`."""

    duration_seconds: float = DEFAULT_CALIBRATION_DURATION_SECONDS
    _started_at: float = field(default_factory=time.monotonic)
    _ear_samples: list[float] = field(default_factory=list)

    def observe(self, result: DetectionResult) -> None:
        if not result.face_present or result.ear is None:
            return
        self._ear_samples.append(result.ear)

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._started_at

    @property
    def is_complete(self) -> bool:
        return self.elapsed_seconds >= self.duration_seconds

    def finish(self) -> CalibrationProfile:
        if len(self._ear_samples) < _MIN_VALID_SAMPLES:
            raise CalibrationIncompleteError(
                detail=f"only {len(self._ear_samples)} valid samples collected"
            )

        baseline_ear = sum(self._ear_samples) / len(self._ear_samples)
        blink_ear_threshold = baseline_ear * _BLINK_THRESHOLD_RATIO
        blink_count = _count_blinks(self._ear_samples, blink_ear_threshold)

        minutes = max(self.elapsed_seconds / 60.0, 1e-6)
        baseline_blink_rate = blink_count / minutes

        return CalibrationProfile(
            baseline_ear=baseline_ear,
            baseline_blink_rate_per_min=baseline_blink_rate,
            blink_ear_threshold=blink_ear_threshold,
            calibrated_at=time.time(),
        )


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
