"""Local SQLite storage for derived metrics only -- never images or video.

All queries are parameterized (never string-built) per the project's OWASP-aligned
security stance. Schema stores break events and periodic blink-rate samples: nothing that
could reconstruct a camera frame lives here.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

from breaktime.core.errors import StorageError
from breaktime.core.types import BreakEvent

DB_DIR = Path.home() / ".breaktime"
DB_FILE = DB_DIR / "data.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS break_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_reason TEXT NOT NULL,
    started_at REAL NOT NULL,
    completed_at REAL,
    verified INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS blink_rate_samples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    blink_rate_per_min REAL NOT NULL
);
"""


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise StorageError(detail=str(exc)) from exc
    finally:
        conn.close()


def record_break_event(event: BreakEvent) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO break_events (trigger_reason, started_at, completed_at, verified) "
            "VALUES (?, ?, ?, ?)",
            (
                event.trigger_reason.name,
                event.started_at,
                event.completed_at,
                int(event.verified),
            ),
        )


def record_blink_rate_sample(timestamp: float, blink_rate_per_min: float) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO blink_rate_samples (timestamp, blink_rate_per_min) VALUES (?, ?)",
            (timestamp, blink_rate_per_min),
        )


def count_verified_breaks_since(since_timestamp: float) -> int:
    with _connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM break_events WHERE verified = 1 AND started_at >= ?",
            (since_timestamp,),
        ).fetchone()
        return int(row[0]) if row else 0


def current_streak_days() -> int:
    """Number of consecutive days (ending today, local time) with a verified break."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT date(started_at, 'unixepoch', 'localtime') AS day "
            "FROM break_events WHERE verified = 1 ORDER BY day DESC"
        ).fetchall()

    if not rows:
        return 0

    days = {row[0] for row in rows}
    streak = 0
    cursor = date.today()
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
