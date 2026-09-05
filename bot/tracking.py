from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message, TelegramObject

from bot.cleanup import track


class TrackIncomingMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]):
        _track_message(event)
        return await handler(event, data)


class TrackOutgoingMiddleware(BaseRequestMiddleware):
    async def __call__(self, make_request, bot, method):
        response = await make_request(bot, method)
        _track_message(response)
        return response


def _track_message(value):
    if isinstance(value, Message) and value.chat.type == ChatType.PRIVATE:
        track(value.chat.id, value.message_id)
