"""Experimental, non-diagnostic facial-tension hint.

Deliberately minimal for v1: this is NOT emotion or depression detection -- that is a
research-stage capability with real ethical and regulatory weight (see docs/ROADMAP.md,
"Explicitly deferred"). It only surfaces a soft, local-only heuristic derived from a couple
of face landmark distances (inner-eyebrow gap relative to face width, a loose proxy for
brow furrowing), and it must stay labeled as experimental everywhere it's surfaced to the
user. Do not extend this into a clinical or diagnostic claim without real validation.
"""

from __future__ import annotations

import numpy as np

from breaktime.core.types import MoodSignal

_LEFT_INNER_BROW = 55
_RIGHT_INNER_BROW = 285
_LEFT_EYE_OUTER = 33
_RIGHT_EYE_OUTER = 263

_RELAXED_BROW_RATIO = 0.42


def estimate_tension(points: np.ndarray, timestamp: float) -> MoodSignal:
    """Return a coarse 0..1 tension heuristic from face landmark points.

    `points` are 2D pixel coordinates for the current frame's landmarks only -- derived
    geometry, not image data, and discarded by the caller immediately after this call.
    """
    face_width = float(np.linalg.norm(points[_LEFT_EYE_OUTER] - points[_RIGHT_EYE_OUTER]))
    if face_width == 0:
        return MoodSignal(timestamp=timestamp, tension_score=None)

    brow_gap = float(np.linalg.norm(points[_LEFT_INNER_BROW] - points[_RIGHT_INNER_BROW]))
    ratio = brow_gap / face_width

    tension = max(0.0, min(1.0, (_RELAXED_BROW_RATIO - ratio) / _RELAXED_BROW_RATIO))
    return MoodSignal(timestamp=timestamp, tension_score=tension)
