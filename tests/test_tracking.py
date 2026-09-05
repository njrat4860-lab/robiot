import pytest
from aiogram.types import Chat, Message

from bot import cleanup
from bot.tracking import TrackIncomingMiddleware, TrackOutgoingMiddleware

CHAT_ID = 42


def make_message(message_id, chat_type="private"):
    return Message.model_construct(
        message_id=message_id,
        date=None,
        chat=Chat.model_construct(id=CHAT_ID, type=chat_type),
    )


@pytest.fixture(autouse=True)
def clean_tracker():
    cleanup.clear(CHAT_ID)
    yield
    cleanup.clear(CHAT_ID)


@pytest.mark.asyncio
async def test_incoming_private_message_is_tracked():
    middleware = TrackIncomingMiddleware()

    async def handler(event, data):
        return None

    await middleware(handler, make_message(7), {})
    assert cleanup.tracked_ids(CHAT_ID) == [7]


@pytest.mark.asyncio
async def test_group_message_is_not_tracked():
    middleware = TrackIncomingMiddleware()

    async def handler(event, data):
        return None

    await middleware(handler, make_message(7, "supergroup"), {})
    assert cleanup.tracked_ids(CHAT_ID) == []


@pytest.mark.asyncio
async def test_sent_message_is_tracked():
    middleware = TrackOutgoingMiddleware()

    async def make_request(bot, method):
        return make_message(11)

    await middleware(make_request, None, None)
    assert cleanup.tracked_ids(CHAT_ID) == [11]


@pytest.mark.asyncio
async def test_non_message_response_is_ignored():
    middleware = TrackOutgoingMiddleware()

    async def make_request(bot, method):
        return True

    assert await middleware(make_request, None, None) is True
    assert cleanup.tracked_ids(CHAT_ID) == []


@pytest.mark.asyncio
async def test_delete_tracked_clears_the_chat_history_buffer():
    deleted = []

    class FakeBot:
        async def delete_messages(self, chat_id, message_ids):
            deleted.extend(message_ids)
            return True

    cleanup.track(CHAT_ID, 1)
    cleanup.track(CHAT_ID, 2)
    await cleanup.delete_tracked(FakeBot(), CHAT_ID, [3])
    assert deleted == [1, 2, 3]
    assert cleanup.tracked_ids(CHAT_ID) == []
