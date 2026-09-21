import time

import pytest

from breaktime.core.types import BreakEvent, TriggerReason
from breaktime.storage import db


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_FILE", tmp_path / "data.db")


def test_record_and_count_verified_breaks():
    now = time.time()
    event = BreakEvent(
        trigger_reason=TriggerReason.TIME_THRESHOLD,
        started_at=now,
        completed_at=now + 20,
        verified=True,
    )
    db.record_break_event(event)

    assert db.count_verified_breaks_since(now - 1) == 1
    assert db.count_verified_breaks_since(now + 100) == 0


def test_unverified_breaks_are_not_counted():
    now = time.time()
    event = BreakEvent(
        trigger_reason=TriggerReason.FATIGUE,
        started_at=now,
        completed_at=None,
        verified=False,
    )
    db.record_break_event(event)

    assert db.count_verified_breaks_since(now - 1) == 0


def test_current_streak_counts_today():
    now = time.time()
    event = BreakEvent(
        trigger_reason=TriggerReason.TIME_THRESHOLD,
        started_at=now,
        completed_at=now,
        verified=True,
    )
    db.record_break_event(event)

    assert db.current_streak_days() == 1
