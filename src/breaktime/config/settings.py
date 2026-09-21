"""Typed, validated user configuration.

This is a local per-user settings file (~/.breaktime/config.json) -- there are no secrets
in this application, so a full env-var/secrets-manager layering scheme would be over-
engineering. Pydantic still earns its place here: it gives validation and clear error
messages if a user hand-edits the file into an invalid state, and it's the single typed
source of truth every other module reads from.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

CONFIG_DIR = Path.home() / ".breaktime"
CONFIG_FILE = CONFIG_DIR / "config.json"


class BreakTimeSettings(BaseModel):
    """User-adjustable settings, persisted locally and editable from the tray menu."""

    continuous_time_threshold_seconds: int = Field(default=1200, ge=60, le=7200)
    fatigue_blink_rate_drop_ratio: float = Field(default=0.5, gt=0, lt=1)
    verified_break_required_seconds: int = Field(default=20, ge=5, le=300)
    verified_break_enabled: bool = True
    mood_hint_enabled: bool = True
    auto_start_enabled: bool = True
    crash_reporting_opt_in: bool = False
    capture_fps: float = Field(default=3.0, ge=1.0, le=10.0)

    @classmethod
    def load(cls) -> BreakTimeSettings:
        """Load settings from disk, falling back to defaults if missing or invalid."""
        if not CONFIG_FILE.exists():
            return cls()
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return cls.model_validate(data)
        except (json.JSONDecodeError, ValueError):
            return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(self.model_dump_json(indent=2), encoding="utf-8")
