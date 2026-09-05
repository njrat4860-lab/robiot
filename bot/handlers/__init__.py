from aiogram import Dispatcher

from bot.handlers import start, rating, profile, admin, pay, feedback


def register_routers(dp: Dispatcher):
    dp.include_router(start.router)
    dp.include_router(rating.router)
    dp.include_router(profile.router)
    dp.include_router(pay.router)
    dp.include_router(admin.router)
    dp.include_router(feedback.router)
