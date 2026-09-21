"""One-time setup/build step: fetch the MediaPipe FaceLandmarker model file.

This is the only place in the project that talks to the network. It is run explicitly by
a contributor during dev setup, or by CI before packaging a release -- never by the
running app itself, which only ever reads the model from local disk afterward. Keeping
this separate from app runtime is what lets the app truthfully claim no background
network calls.

Usage: python scripts/download_model.py
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
_MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "breaktime"
    / "vision"
    / "models"
    / "face_landmarker.task"
)
# SHA-256 of the file at the URL above, pinned so a compromised or altered download is
# detected rather than silently bundled into the app.
_EXPECTED_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"


def main() -> int:
    _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    if _MODEL_PATH.exists() and _sha256(_MODEL_PATH) == _EXPECTED_SHA256:
        print(f"Model already present and verified at {_MODEL_PATH}")
        return 0

    print(f"Downloading {_MODEL_URL} ...")
    urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)  # noqa: S310 -- fixed, hardcoded HTTPS URL

    digest = _sha256(_MODEL_PATH)
    if digest != _EXPECTED_SHA256:
        _MODEL_PATH.unlink(missing_ok=True)
        print(
            f"Checksum mismatch (got {digest}, expected {_EXPECTED_SHA256}) -- "
            "deleted the downloaded file. Not proceeding.",
            file=sys.stderr,
        )
        return 1

    print(f"Downloaded and verified: {_MODEL_PATH}")
    return 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
