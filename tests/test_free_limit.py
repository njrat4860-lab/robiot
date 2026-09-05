import tempfile
from pathlib import Path

import pytest

import bot.db as db_module
from bot.db import Database

HOURS_24 = 24 * 3600


@pytest.mark.asyncio
async def test_one_rating_per_24_hours(monkeypatch):
    now = 1_700_000_000
    monkeypatch.setattr(db_module.time, "time", lambda: now)
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        assert await db.consume_free_rating(1, 1, HOURS_24) is True
        assert await db.consume_free_rating(1, 1, HOURS_24) is False
        assert await db.free_remaining(1, 1, HOURS_24) == 0
        await db.close()


@pytest.mark.asyncio
async def test_window_resets_after_configured_hours(monkeypatch):
    now = [1_700_000_000]
    monkeypatch.setattr(db_module.time, "time", lambda: now[0])
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        assert await db.consume_free_rating(1, 1, HOURS_24) is True
        now[0] += HOURS_24
        assert await db.free_remaining(1, 1, HOURS_24) == 1
        assert await db.consume_free_rating(1, 1, HOURS_24) is True
        await db.close()


@pytest.mark.asyncio
async def test_free_limit_setting_is_stored_as_count_and_hours():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        await db.set_setting("free_limit_count", "1")
        await db.set_setting("free_limit_hours", "24")
        assert await db.free_limit() == (1, 24)
        await db.close()


@pytest.mark.asyncio
async def test_legacy_hourly_limit_is_migrated():
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp) / "test.db")
        db = Database(path)
        await db.connect()
        await db.conn.execute("DELETE FROM settings WHERE key = 'free_limit_count'")
        await db.set_setting("free_limit_per_hour", "7")
        await db.close()

        migrated = Database(path)
        await migrated.connect()
        assert await migrated.free_limit() == (7, 1)
        await migrated.close()


@pytest.mark.asyncio
async def test_metric_toggle_round_trip():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        await db.set_metric_enabled("frontal", "male", "skin", False)
        assert await db.disabled_metrics("frontal", "male") == {"skin"}
        assert await db.disabled_metrics("frontal", "female") == set()
        await db.set_metric_enabled("frontal", "male", "skin", True)
        assert await db.disabled_metrics("frontal", "male") == set()
        await db.close()
