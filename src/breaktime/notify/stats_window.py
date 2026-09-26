"""Native read-only stats popup for the tray menu's "Today's stats" item.

Uses stdlib Tkinter (already bundled via the packaging pipeline's Tk dependency) rather
than a new GUI dependency for one small window. Read-only: shows numbers already
computed from local SQLite data (storage/db.py) -- no new data collection, no network
call, consistent with the rest of the project's privacy stance.
"""

from __future__ import annotations

import tkinter as tk
from datetime import date, datetime
from datetime import time as dt_time

from breaktime.storage.db import count_verified_breaks_since, current_streak_days


def show_stats_window() -> None:
    """Blocking call -- invoke from a background thread, never the vision loop thread."""
    since_midnight = datetime.combine(date.today(), dt_time.min).timestamp()
    today_count = count_verified_breaks_since(since_midnight)
    streak = current_streak_days()

    root = tk.Tk()
    root.title("Break-Time stats")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    tk.Label(root, text="Break-Time", font=("Segoe UI", 14, "bold")).pack(padx=24, pady=(18, 6))
    tk.Label(root, text=f"Verified breaks today: {today_count}", font=("Segoe UI", 11)).pack(
        padx=24, pady=4
    )
    streak_label = f"Current streak: {streak} day{'s' if streak != 1 else ''}"
    tk.Label(root, text=streak_label, font=("Segoe UI", 11)).pack(padx=24, pady=(4, 18))
    tk.Button(root, text="Close", command=root.destroy, width=10).pack(pady=(0, 18))

    root.eval("tk::PlaceWindow . center")
    root.mainloop()
