"""Webcam frame capture.

Sampled at a low, configurable frame rate (default ~3fps) rather than full 30fps -- this
app only needs to notice fatigue trends over minutes, not react to every frame, so there's
no reason to spend CPU/battery analyzing 30 frames a second.

Deliberately the one module in this codebase excluded from unit test coverage (see
pyproject.toml) -- it's a thin boundary around cv2.VideoCapture, verified manually per the
project's verification steps rather than through synthetic fixtures.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import cast

import cv2
import numpy as np
import numpy.typing as npt

from breaktime.core.errors import CameraUnavailableError
from breaktime.core.logging import get_logger, log_event

_logger = get_logger("vision.capture")

Frame = npt.NDArray[np.uint8]


@contextmanager
def open_camera(device_index: int = 0) -> Iterator[cv2.VideoCapture]:
    """Open the webcam for the duration of the `with` block, always releasing it after."""
    capture = cv2.VideoCapture(device_index)
    if not capture.isOpened():
        raise CameraUnavailableError(
            detail=f"cv2.VideoCapture could not open device {device_index}"
        )
    log_event(_logger, "camera_opened", device_index=device_index)
    try:
        yield capture
    finally:
        capture.release()
        log_event(_logger, "camera_released", device_index=device_index)


def frames(capture: cv2.VideoCapture, fps: float) -> Iterator[Frame]:
    """Yield frames at approximately `fps`, discarding the rest.

    Every yielded frame must be analyzed and discarded by the caller -- this module never
    stores a frame itself. Reads happen continuously (not throttled with sleep) to keep
    draining the camera driver's buffer and avoid processing stale frames; only the
    *yield* is throttled to the target rate.
    """
    interval = 1.0 / fps
    next_due = time.monotonic()
    while True:
        ok, frame = capture.read()
        if not ok:
            log_event(_logger, "camera_read_failed")
            return
        now = time.monotonic()
        if now >= next_due:
            next_due = now + interval
            # cv2's stubs type read() loosely (Mat | ndarray[...floating...]); a webcam
            # frame is always an 8-bit BGR array in practice.
            yield cast(Frame, frame)
