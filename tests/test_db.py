import tempfile
from pathlib import Path

import pytest

import bot.db as db_module
from bot.db import Database


@pytest.mark.asyncio
async def test_free_rating_window():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        await db.ensure_user(1)
        assert await db.consume_free_rating(1, 3) is True
        assert await db.consume_free_rating(1, 3) is True
        assert await db.consume_free_rating(1, 3) is True
        assert await db.consume_free_rating(1, 3) is False
        assert await db.free_remaining(1, 3) == 0
        await db.close()


@pytest.mark.asyncio
async def test_credits():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        await db.ensure_user(1)
        assert await db.consume_credit(1) is False
        await db.add_credit(1)
        assert await db.consume_credit(1) is True
        assert await db.consume_credit(1) is False
        await db.close()


@pytest.mark.asyncio
async def test_rating_persistence():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        await db.ensure_user(1)
        await db.add_rating(1, "frontal", "male", 4.5, 0.6, {"fwhr": 1.9}, ["warn"], 0)
        ratings = await db.recent_ratings(1, 10)
        assert len(ratings) == 1
        assert ratings[0]["psl"] == 4.5
        assert await db.total_ratings() == 1
        await db.close()


@pytest.mark.asyncio
async def test_rating_history_keeps_three_free_and_five_paid(monkeypatch):
    now = 2_000_000_000
    monkeypatch.setattr(db_module.time, "time", lambda: now)
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        for index in range(6):
            await db.add_rating(1, "frontal", "male", float(index), 0.5, {}, [], 0)
        for index in range(6):
            await db.add_rating(1, "frontal", "male", float(100 + index), 0.5, {}, [], 1)
        ratings = await db.recent_ratings(1)
        free = [rating for rating in ratings if rating["paid"] == 0]
        paid = [rating for rating in ratings if rating["paid"] == 1]
        assert len(free) == 3
        assert len(paid) == 5
        assert [rating["psl"] for rating in free] == [5.0, 4.0, 3.0]
        assert [rating["psl"] for rating in paid] == [105.0, 104.0, 103.0, 102.0, 101.0]
        await db.close()


@pytest.mark.asyncio
async def test_rating_history_removes_old_free_and_paid(monkeypatch):
    now = 2_000_000_000
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        monkeypatch.setattr(db_module.time, "time", lambda: now - db_module.FREE_RATING_TTL_SECONDS - 10)
        await db.connect()
        await db.add_rating(1, "frontal", "male", 1.0, 0.5, {}, [], 0)
        monkeypatch.setattr(db_module.time, "time", lambda: now - db_module.PAID_RATING_TTL_SECONDS - 10)
        await db.add_rating(1, "frontal", "male", 2.0, 0.5, {}, [], 1)
        monkeypatch.setattr(db_module.time, "time", lambda: now)
        await db.purge_expired_ratings()
        assert await db.recent_ratings(1) == []
        await db.close()


@pytest.mark.asyncio
async def test_ensure_user_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        await db.ensure_user(1)
        await db.ensure_user(1)
        user = await db.get_user(1)
        assert user["user_id"] == 1
        await db.close()


@pytest.mark.asyncio
async def test_delete_rating_is_scoped_to_owner():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        await db.add_rating(1, "frontal", "male", 7.0, 0.8, {}, [], 0)
        ratings = await db.recent_ratings(1)
        rating_id = ratings[0]["id"]
        assert await db.delete_rating(2, rating_id) is False
        assert len(await db.recent_ratings(1)) == 1
        assert await db.delete_rating(1, rating_id) is True
        assert await db.recent_ratings(1) == []
        await db.close()


@pytest.mark.asyncio
async def test_unlimited_access(monkeypatch):
    now = 2_000_000_000
    monkeypatch.setattr(db_module.time, "time", lambda: now)
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        await db.set_unlimited(1, now + 100)
        assert await db.has_unlimited(1) is True
        await db.set_unlimited(1, now - 100)
        assert await db.has_unlimited(1) is False
        await db.set_unlimited(1, -1)
        assert await db.has_unlimited(1) is True
        await db.close()


@pytest.mark.asyncio
async def test_tickets_flow():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        await db.add_ticket(1, "bug")
        tickets = await db.open_tickets()
        assert len(tickets) == 1
        ticket_id = tickets[0]["id"]
        assert await db.answer_ticket(ticket_id, "answer") is True
        ticket = await db.get_ticket(ticket_id)
        assert ticket["status"] == "answered"
        assert ticket["answer"] == "answer"
        await db.close()


@pytest.mark.asyncio
async def test_sponsors_and_settings():
    with tempfile.TemporaryDirectory() as tmp:
        db = Database(str(Path(tmp) / "test.db"))
        await db.connect()
        await db.add_sponsor("some_channel", "Канал", 1)
        sponsors = await db.sponsors()
        assert len(sponsors) == 1
        await db.set_setting("price_stars", "75")
        assert await db.get_setting("price_stars") == "75"
        await db.remove_sponsor(sponsors[0]["id"])
        assert len(await db.sponsors()) == 0
        await db.close()
