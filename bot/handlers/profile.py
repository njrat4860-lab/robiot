from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot import texts
from bot.cleanup import delete_tracked
from bot.keyboards import profile_history_keyboard

router = Router()


@router.callback_query(F.data == "profile")
async def on_profile(callback: CallbackQuery, db, bot):
    await delete_tracked(bot, callback.message.chat.id, [callback.message.message_id])
    await _send_profile(callback, db, bot)


@router.callback_query(F.data.startswith("profile_gender:"))
async def on_profile_gender(callback: CallbackQuery, db, bot):
    gender = callback.data.split(":", 1)[1]
    if gender not in ("male", "female"):
        await callback.answer()
        return
    await db.set_gender(callback.from_user.id, gender)
    if callback.message.caption is not None:
        await callback.message.delete()
        await _send_profile(callback, db, bot)
    else:
        user = await db.ensure_user(callback.from_user.id)
        ratings = await db.recent_ratings(callback.from_user.id)
        await callback.message.edit_text(
            texts.profile_history(ratings, user["gender"]),
            reply_markup=profile_history_keyboard(ratings),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("rating_del:"))
async def on_rating_delete(callback: CallbackQuery, db, bot):
    rating_id = _callback_id(callback.data, 1)
    if rating_id is None:
        await callback.answer()
        return
    await db.delete_rating(callback.from_user.id, rating_id)
    await callback.message.delete()
    await _send_profile(callback, db, bot)


def _callback_id(data, index):
    parts = data.split(":")
    if len(parts) <= index or not parts[index].isdigit():
        return None
    return int(parts[index])


async def _send_profile(callback, db, bot):
    user = await db.ensure_user(callback.from_user.id)
    ratings = await db.recent_ratings(callback.from_user.id)
    await bot.send_message(
        callback.message.chat.id,
        texts.profile_history(ratings, user["gender"]),
        reply_markup=profile_history_keyboard(ratings),
    )
    await callback.answer()
