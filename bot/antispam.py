import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

MIN_EVENT_INTERVAL = 0.45
WINDOW_SECONDS = 8.0
WINDOW_LIMIT = 12
IMPORTANT_PREFIXES = (
    "rate",
    "gender:",
    "mode:",
    "profile_gender:",
    "sponsor_check",
    "menu",
    "result_back",
    "queue_cancel",
)


class AntiSpamMiddleware(BaseMiddleware):
    def __init__(self):
        self.events = defaultdict(deque)
        self.last_event = {}

    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]):
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)
        if _important_callback(event):
            return await handler(event, data)
        now = time.monotonic()
        if self._too_fast(user.id, now):
            return None
        return await handler(event, data)

    def _too_fast(self, user_id, now):
        last = self.last_event.get(user_id, 0.0)
        if now - last < MIN_EVENT_INTERVAL:
            return True
        self.last_event[user_id] = now
        events = self.events[user_id]
        while events and now - events[0] > WINDOW_SECONDS:
            events.popleft()
        events.append(now)
        return len(events) > WINDOW_LIMIT


def _important_callback(event):
    if not isinstance(event, CallbackQuery):
        return False
    data = event.data or ""
    return any(data == prefix or data.startswith(prefix) for prefix in IMPORTANT_PREFIXES)
