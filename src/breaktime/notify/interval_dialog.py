"""A tiny modal dialog for entering a custom break interval in minutes.

Uses stdlib Tkinter (already bundled via the packaging pipeline's Tk dependency) rather
than pulling in a new GUI toolkit for a single input box.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog


def ask_custom_interval_minutes(current_minutes: int) -> int | None:
    """Blocking; returns the chosen minute count, or None if cancelled."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return simpledialog.askinteger(
            "Break-Time",
            "Break reminder interval, in minutes (1-120):",
            initialvalue=current_minutes,
            minvalue=1,
            maxvalue=120,
            parent=root,
        )
    finally:
        root.destroy()
