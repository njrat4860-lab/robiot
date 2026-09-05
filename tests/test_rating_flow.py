import numpy as np
import pytest

from bot.handlers import rating

NO_FACE_RESULT = {
    "mode": "frontal",
    "gender": "male",
    "psl": None,
    "quality": None,
    "metrics": {},
    "warnings": ["лицо не найдено - сфотографируй анфас крупным планом"],
    "pose": {},
    "lighting": {},
    "landmarks": None,
    "contour": None,
    "profile_points": None,
    "hairline": None,
    "image": None,
}


class FakeUser:
    id = 1


class FakeChat:
    id = 10


class FakeMessage:
    def __init__(self):
        self.from_user = FakeUser()
        self.chat = FakeChat()
        self.message_id = 100
        self.texts = []
        self.photos = 0
        self.documents = 0

    async def answer(self, text, reply_markup=None):
        self.texts.append(text)
        return self

    async def answer_photo(self, photo, caption=None, reply_markup=None):
        self.photos += 1
        return self

    async def answer_document(self, document, caption=None):
        self.documents += 1
        return self

    async def edit_text(self, text, reply_markup=None):
        return self

    async def delete(self):
        return None


class FakeState:
    def __init__(self):
        self.data = {}

    async def get_data(self):
        return self.data

    async def clear(self):
        self.data = {}


class FakeDatabase:
    def __init__(self):
        self.consumed = 0
        self.ratings = 0

    async def disabled_metrics(self, mode, gender):
        return set()

    async def free_limit(self):
        return 1, 1

    async def consume_free_rating(self, user_id, limit, window_seconds):
        self.consumed += 1
        return True

    async def add_rating(self, *args):
        self.ratings += 1


@pytest.mark.asyncio
async def test_missing_face_sends_no_report_and_keeps_the_request(monkeypatch):
    message = FakeMessage()
    database = FakeDatabase()

    async def fake_download(bot, file_id):
        return np.zeros((8, 8, 3), dtype=np.uint8)

    async def fake_analysis(pipeline_analyze, image_rgb, gender, mode, disabled_metrics=None):
        return dict(NO_FACE_RESULT)

    monkeypatch.setattr(rating, "_download_image", fake_download)
    monkeypatch.setattr(rating, "run_analysis", fake_analysis)

    await rating._run_and_reply(message, FakeState(), database, None, "file", "frontal", "male", "free", message)

    assert message.documents == 0
    assert message.photos == 0
    assert database.consumed == 0
    assert database.ratings == 0
    assert any("лицо не найдено" in text for text in message.texts)


@pytest.mark.asyncio
async def test_accepted_photo_is_deleted_when_analysis_starts(monkeypatch):
    message = FakeMessage()
    database = FakeDatabase()
    deleted = {}

    async def fake_delete_tracked(bot, chat_id, extra_ids=()):
        deleted["chat_id"] = chat_id
        deleted["ids"] = list(extra_ids)

    class FullQueue:
        async def enqueue(self, user_id, size, notifier):
            return rating.QUEUE_FULL

    async def fake_sponsor_ok(bot, user_id, db):
        return True

    async def fake_access(db, user_id):
        return "free"

    async def fake_mode_enabled(db, mode, gender):
        return True

    async def fake_queue_size(db):
        return 1

    async def fake_ensure_user(user_id):
        return {"gender": "male"}

    database.ensure_user = fake_ensure_user
    monkeypatch.setattr(rating, "delete_tracked", fake_delete_tracked)
    monkeypatch.setattr(rating, "_QUEUE", FullQueue())
    monkeypatch.setattr(rating, "_sponsor_ok", fake_sponsor_ok)
    monkeypatch.setattr(rating, "_resolve_access", fake_access)
    monkeypatch.setattr(rating, "_mode_enabled", fake_mode_enabled)
    monkeypatch.setattr(rating, "_queue_size", fake_queue_size)

    await rating._process_image(message, FakeState(), database, None, "file", 1000)

    assert deleted["chat_id"] == message.chat.id
    assert deleted["ids"] == [message.message_id]
