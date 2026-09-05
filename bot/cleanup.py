from collections import defaultdict, deque

TRACKED = defaultdict(lambda: deque(maxlen=200))
DELETE_BATCH = 100


def track(chat_id, message_id):
    TRACKED[chat_id].append(message_id)


def tracked_ids(chat_id):
    return list(TRACKED[chat_id])


def clear(chat_id):
    TRACKED[chat_id].clear()


async def delete_tracked(bot, chat_id, extra_ids=()):
    message_ids = tracked_ids(chat_id) + list(extra_ids)
    clear(chat_id)
    if message_ids:
        await delete_messages(bot, chat_id, message_ids)


async def delete_messages(bot, chat_id, message_ids):
    unique = sorted(set(message_ids))
    for index in range(0, len(unique), DELETE_BATCH):
        batch = unique[index:index + DELETE_BATCH]
        try:
            await bot.delete_messages(chat_id=chat_id, message_ids=batch)
        except Exception:
            await _delete_one_by_one(bot, chat_id, batch)


async def _delete_one_by_one(bot, chat_id, message_ids):
    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            continue
