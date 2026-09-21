"""Per-frame vision analysis: face presence, blink (EAR), gaze, and head pose.

Built on MediaPipe's Tasks API (`FaceLandmarker`), which requires a local model file --
see scripts/download_model.py. That script is a one-time setup/build step run by
contributors or CI, never something the running app does itself: the app only ever reads
the model from local disk, consistent with the project's no-runtime-network-calls stance.

Takes a single BGR frame, returns a DetectionResult (plus an optional MoodSignal), and
never retains or returns the frame itself. This is the privacy boundary between "camera
data" and everything downstream, which only ever sees derived numeric/boolean signals.
"""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.core.base_options import BaseOptions

from breaktime.core.errors import ModelNotFoundError
from breaktime.core.types import DetectionResult, MoodSignal
from breaktime.mood.signal import estimate_tension
from breaktime.vision.capture import Frame

MODEL_PATH = Path(__file__).parent / "models" / "face_landmarker.task"

# Landmark indices for a classic 6-point EAR calculation, ordered
# [corner, top1, top2, corner, bottom2, bottom1] so that
# EAR = (|top1-bottom1| + |top2-bottom2|) / (2 * |corner-corner|).
# FaceLandmarker outputs the same 478-point topology (iris points included by default)
# as the legacy FaceMesh(refine_landmarks=True), so these indices carry over unchanged.
_LEFT_EYE = [33, 160, 158, 133, 153, 144]
_RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# Landmarks + matching generic 3D face model points used for solvePnP head-pose
# estimation. The 3D points are an approximate average face geometry (not user-specific)
# -- sufficient for a coarse "facing the screen or not" signal, not precision tracking.
_POSE_LANDMARKS = [1, 152, 33, 263, 61, 291]
_MODEL_POINTS_3D = np.array(
    [
        (0.0, 0.0, 0.0),
        (0.0, -330.0, -65.0),
        (-225.0, 170.0, -135.0),
        (225.0, 170.0, -135.0),
        (-150.0, -150.0, -125.0),
        (150.0, -150.0, -125.0),
    ],
    dtype=np.float64,
)

_GAZE_ON_SCREEN_YAW_DEG = 20.0
_GAZE_ON_SCREEN_PITCH_DEG = 20.0


class FaceDetector:
    """Wraps a MediaPipe FaceLandmarker instance. Create once, call `analyze` per frame."""

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        if not model_path.exists():
            raise ModelNotFoundError(detail=f"model file not found at {model_path}")

        options = mp_vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=mp_vision.RunningMode.IMAGE,
            num_faces=1,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)

    def close(self) -> None:
        self._landmarker.close()

    def __enter__(self) -> FaceDetector:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def analyze(
        self, frame: Frame, *, include_mood: bool = False
    ) -> tuple[DetectionResult, MoodSignal | None]:
        timestamp = time.time()
        height, width = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)

        if not result.face_landmarks:
            return (
                DetectionResult(
                    timestamp=timestamp,
                    face_present=False,
                    ear=None,
                    gaze_on_screen=None,
                    head_yaw_deg=None,
                    head_pitch_deg=None,
                ),
                None,
            )

        landmarks = result.face_landmarks[0]
        points = np.array([(lm.x * width, lm.y * height) for lm in landmarks])

        ear = _eye_aspect_ratio(points)
        yaw_deg, pitch_deg = _head_pose(points, width, height)
        gaze_on_screen = (
            abs(yaw_deg) <= _GAZE_ON_SCREEN_YAW_DEG and abs(pitch_deg) <= _GAZE_ON_SCREEN_PITCH_DEG
        )

        detection = DetectionResult(
            timestamp=timestamp,
            face_present=True,
            ear=ear,
            gaze_on_screen=gaze_on_screen,
            head_yaw_deg=yaw_deg,
            head_pitch_deg=pitch_deg,
        )
        mood = estimate_tension(points, timestamp) if include_mood else None
        return detection, mood


def _eye_aspect_ratio(points: np.ndarray) -> float:
    """Average Eye Aspect Ratio across both eyes. Lower means more closed / a blink."""
    left = _single_eye_ratio(points, _LEFT_EYE)
    right = _single_eye_ratio(points, _RIGHT_EYE)
    return (left + right) / 2.0


def _single_eye_ratio(points: np.ndarray, indices: list[int]) -> float:
    p = points[indices]
    vertical_1 = np.linalg.norm(p[1] - p[5])
    vertical_2 = np.linalg.norm(p[2] - p[4])
    horizontal = np.linalg.norm(p[0] - p[3])
    if horizontal == 0:
        return 0.0
    return float((vertical_1 + vertical_2) / (2.0 * horizontal))


def _head_pose(points: np.ndarray, width: int, height: int) -> tuple[float, float]:
    """Coarse (yaw_deg, pitch_deg) via solvePnP against a generic 3D face model."""
    image_points = points[_POSE_LANDMARKS].astype(np.float64)
    focal_length = float(width)
    center = (width / 2.0, height / 2.0)
    camera_matrix = np.array(
        [[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]],
        dtype=np.float64,
    )
    dist_coeffs = np.zeros((4, 1))

    ok, rotation_vec, _translation_vec = cv2.solvePnP(
        _MODEL_POINTS_3D, image_points, camera_matrix, dist_coeffs
    )
    if not ok:
        return 0.0, 0.0

    rotation_matrix, _ = cv2.Rodrigues(rotation_vec)
    sy = np.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
    pitch = np.degrees(np.arctan2(-rotation_matrix[2, 0], sy))
    yaw = np.degrees(np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0]))
    return float(yaw), float(pitch)
