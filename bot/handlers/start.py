from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from bot import texts
from bot.cleanup import delete_tracked
from bot.handlers.rating import cancel_queued
from bot.keyboards import main_menu

router = Router()


@router.message(CommandStart())
async def on_start(message: Message, db, admin_ids, bot, state: FSMContext):
    await state.clear()
    await db.ensure_user(message.from_user.id)
    await cancel_queued(message.from_user.id)
    await delete_tracked(bot, message.chat.id, [message.message_id])
    await message.answer(
        texts.START,
        reply_markup=main_menu(message.from_user.id in admin_ids),
    )


@router.callback_query(F.data == "result_back")
async def on_result_back(callback: CallbackQuery, db, admin_ids, state: FSMContext, bot):
    await _back_to_main(callback, db, admin_ids, state, bot)


@router.callback_query(F.data == "menu")
async def on_menu(callback: CallbackQuery, db, admin_ids, state: FSMContext, bot):
    await _back_to_main(callback, db, admin_ids, state, bot)


async def _back_to_main(callback, db, admin_ids, state, bot):
    await state.clear()
    await db.ensure_user(callback.from_user.id)
    cancelled = await cancel_queued(callback.from_user.id)
    chat_id = callback.message.chat.id
    await delete_tracked(bot, chat_id, [callback.message.message_id])
    if cancelled:
        await bot.send_message(chat_id, texts.QUEUE_CANCELLED)
    await bot.send_message(
        chat_id,
        texts.MAIN_MENU,
        reply_markup=main_menu(callback.from_user.id in admin_ids),
    )
    await callback.answer()
