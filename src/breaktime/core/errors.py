"""Typed exceptions with an explicit split between user-facing and internal detail.

Per the project's OWASP-aligned error handling stance: users see a short, generic,
actionable message; the full detail (which may include stack traces or internal state,
but never camera/frame data) goes only to the local log file.
"""

from __future__ import annotations


class BreakTimeError(Exception):
    """Base class for all Break-Time errors.

    `user_message` is safe to show in a toast/dialog. `detail`, if given, is what gets
    logged -- keep it internal-only, never surface it directly to the user.
    """

    def __init__(self, user_message: str, *, detail: str | None = None) -> None:
        super().__init__(detail or user_message)
        self.user_message = user_message


class CameraUnavailableError(BreakTimeError):
    """The webcam could not be opened or read from."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            "Could not access your webcam. Check camera permissions and make sure no "
            "other app is using it.",
            detail=detail,
        )


class ModelNotFoundError(BreakTimeError):
    """The local MediaPipe FaceLandmarker model file is missing."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            "Break-Time's face detection model is missing. Run "
            "`python scripts/download_model.py` (contributors) or reinstall the app "
            "(end users) to restore it.",
            detail=detail,
        )


class CalibrationIncompleteError(BreakTimeError):
    """First-run calibration did not collect enough valid samples."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(
            "Calibration did not complete. Please try again facing the camera in a well-lit area.",
            detail=detail,
        )


class StorageError(BreakTimeError):
    """Reading or writing local settings/history data failed."""

    def __init__(self, detail: str | None = None) -> None:
        super().__init__("Could not save your local data.", detail=detail)
