import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramUnauthorizedError
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import load_config
from bot.db import Database
from bot.antispam import AntiSpamMiddleware
from bot.handlers import register_routers
from bot.tracking import TrackIncomingMiddleware, TrackOutgoingMiddleware
from engine.calibration import load_calibration


async def main():
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    if not config.token:
        raise RuntimeError("BOT_TOKEN не задан")
    logging.info("calibration %s", load_calibration().get("version", "unknown"))

    db = Database(config.db_path)
    await db.connect()

    bot = Bot(token=config.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bot.session.middleware(TrackOutgoingMiddleware())
    dp = Dispatcher(storage=MemoryStorage())
    dp["db"] = db
    dp["admin_ids"] = config.admin_ids
    antispam = AntiSpamMiddleware()
    dp.message.outer_middleware(TrackIncomingMiddleware())
    dp.message.middleware(antispam)
    dp.callback_query.middleware(antispam)
    register_routers(dp)

    try:
        await dp.start_polling(bot)
    except TelegramUnauthorizedError as error:
        raise RuntimeError("BOT_TOKEN неверный, токен отозван или BotHost запускает переменную не от этого бота") from error

if __name__ == "__main__":
    asyncio.run(main())
