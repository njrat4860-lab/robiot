from html import escape

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from bot import texts
from bot.cleanup import delete_tracked
from bot.keyboards import back_to_menu
from bot.states import AdminFlow, FeedbackFlow

router = Router()

MAX_TICKET_TEXT = 1200
MAX_TICKET_ANSWER = 1200


@router.callback_query(F.data == "feedback")
async def on_feedback(callback: CallbackQuery, state: FSMContext, bot):
    await state.set_state(FeedbackFlow.awaiting_message)
    await delete_tracked(bot, callback.message.chat.id, [callback.message.message_id])
    await bot.send_message(
        callback.message.chat.id,
        "<b>Напиши баг или идею одним сообщением</b>",
        reply_markup=back_to_menu(),
    )
    await callback.answer()


@router.message(FeedbackFlow.awaiting_message)
async def on_feedback_message(message: Message, state: FSMContext, db, bot):
    text = (message.text or message.caption or "").strip()
    if not text:
        await _screen(message, bot, "<b>Нужен текст</b>")
        return
    await db.add_ticket(message.from_user.id, text[:MAX_TICKET_TEXT])
    await state.clear()
    await _screen(message, bot, "<b>Принял</b>")


@router.callback_query(F.data == "admin:tickets")
async def on_admin_tickets(callback: CallbackQuery, db, admin_ids):
    if callback.from_user.id not in admin_ids:
        await callback.answer()
        return
    tickets = await db.open_tickets(10)
    await callback.message.edit_text(_tickets_text(tickets), reply_markup=_tickets_keyboard(tickets))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:ticket:"))
async def on_admin_ticket(callback: CallbackQuery, db, admin_ids):
    if callback.from_user.id not in admin_ids:
        await callback.answer()
        return
    ticket_id = _callback_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer()
        return
    ticket = await db.get_ticket(ticket_id)
    if ticket is None:
        await callback.answer()
        return
    await callback.message.edit_text(_ticket_text(ticket), reply_markup=_ticket_keyboard(ticket))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:ticket_reply:"))
async def on_admin_ticket_reply(callback: CallbackQuery, state: FSMContext, admin_ids):
    if callback.from_user.id not in admin_ids:
        await callback.answer()
        return
    ticket_id = _callback_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer()
        return
    await state.set_state(AdminFlow.awaiting_ticket_reply)
    await state.update_data(ticket_id=ticket_id)
    await callback.message.edit_text("<b>Напиши ответ пользователю</b>", reply_markup=back_to_menu())
    await callback.answer()


@router.message(AdminFlow.awaiting_ticket_reply)
async def on_admin_ticket_answer(message: Message, state: FSMContext, db, bot, admin_ids):
    if message.from_user.id not in admin_ids:
        await state.clear()
        return
    answer = (message.text or "").strip()
    if not answer:
        await _screen(message, bot, "<b>Нужен текст</b>")
        return
    data = await state.get_data()
    ticket = await db.get_ticket(data["ticket_id"])
    if ticket is None:
        await state.clear()
        await _screen(message, bot, "<b>Тикет не найден</b>")
        return
    if await db.answer_ticket(ticket["id"], answer[:MAX_TICKET_ANSWER]):
        await bot.send_message(ticket["user_id"], f"<b>Ответ по обращению:</b>\n<b>{escape(answer[:MAX_TICKET_ANSWER])}</b>")
    await state.clear()
    await _screen(message, bot, "<b>Ответ отправлен</b>")


@router.callback_query(F.data.startswith("admin:ticket_close:"))
async def on_admin_ticket_close(callback: CallbackQuery, db, admin_ids):
    if callback.from_user.id not in admin_ids:
        await callback.answer()
        return
    ticket_id = _callback_id(callback.data, 2)
    if ticket_id is None:
        await callback.answer()
        return
    await db.close_ticket(ticket_id)
    tickets = await db.open_tickets(10)
    await callback.message.edit_text(_tickets_text(tickets), reply_markup=_tickets_keyboard(tickets))
    await callback.answer()


def _callback_id(data, index):
    parts = data.split(":")
    if len(parts) <= index or not parts[index].isdigit():
        return None
    return int(parts[index])


async def _screen(message, bot, text):
    await delete_tracked(bot, message.chat.id)
    await message.answer(text, reply_markup=back_to_menu())


def _tickets_text(tickets):
    if not tickets:
        return "<b>Открытых тикетов нет</b>"
    lines = ["<b>Тикеты</b>"]
    for ticket in tickets:
        lines.append(f"<b>#{ticket['id']} от {ticket['user_id']}</b>")
    return "\n".join(lines)


def _tickets_keyboard(tickets):
    buttons = []
    for ticket in tickets:
        buttons.append([InlineKeyboardButton(text=f"◈ #{ticket['id']}", callback_data=f"admin:ticket:{ticket['id']}")])
    buttons.append([InlineKeyboardButton(text="⭠ Назад", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _ticket_text(ticket):
    return f"<b>Тикет #{ticket['id']}</b>\n<b>Пользователь: {ticket['user_id']}</b>\n<b>{escape(ticket['text'])}</b>"


def _ticket_keyboard(ticket):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✦ Ответить", callback_data=f"admin:ticket_reply:{ticket['id']}")],
            [InlineKeyboardButton(text="⊘ Закрыть", callback_data=f"admin:ticket_close:{ticket['id']}")],
            [InlineKeyboardButton(text="⭠ Назад", callback_data="admin:tickets")],
        ]
    )
