import time

from aiogram import Router, F
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from bot import texts
from bot.keyboards import admin_menu_keyboard, back_to_menu
from bot.sponsors import normalize_sponsor_channel, valid_sponsor_channel
from bot.cleanup import delete_tracked
from bot.states import AdminFlow
from engine.calibration import load_calibration

router = Router()

MIN_STARS_PRICE = 1
MAX_STARS_PRICE = 2500
MIN_FREE_LIMIT = 0
MAX_FREE_LIMIT = 1000
MIN_LIMIT_HOURS = 1
MAX_LIMIT_HOURS = 720
MIN_QUEUE_SIZE = 1
MAX_QUEUE_SIZE = 50
MODES = ("frontal", "profile")
GENDERS = ("male", "female")
MODE_WORDS = {"анфас": "frontal", "frontal": "frontal", "профиль": "profile", "profile": "profile"}
GENDER_WORDS = {"мужской": "male", "male": "male", "женский": "female", "female": "female"}
STATE_WORDS = {"вкл": True, "on": True, "выкл": False, "off": False}
DISABLED_METRICS_PREVIEW = 30


async def _screen(message, bot, text):
    await delete_tracked(bot, message.chat.id)
    await message.answer(text, reply_markup=back_to_menu())


async def _is_admin(user_id, admin_ids):
    return user_id in admin_ids


@router.callback_query(F.data == "admin")
async def on_admin(callback: CallbackQuery, db, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    count, hours = await db.free_limit()
    await callback.message.edit_text(
        texts.admin_menu(
            (await db.get_setting("paid_enabled")) == "1",
            (await db.get_setting("free_enabled")) == "1",
            await db.get_setting("price_stars"),
            count,
            hours,
            await db.get_setting("queue_size"),
            await _mode_states(db),
        ),
        reply_markup=admin_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def on_stats(callback: CallbackQuery, db, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    await callback.message.edit_text(
        texts.admin_stats(
            await db.total_users(),
            await db.total_ratings(),
            await db.average_psl(),
            await db.rating_counts_by_mode(),
        ),
        reply_markup=back_to_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:price")
async def on_price(callback: CallbackQuery, state: FSMContext, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    await state.set_state(AdminFlow.awaiting_price)
    await callback.message.edit_text("<b>Отправь цену в Stars</b>", reply_markup=back_to_menu())
    await callback.answer()


@router.message(AdminFlow.awaiting_price)
async def on_price_input(message: Message, state: FSMContext, db, bot, admin_ids):
    if not await _is_admin(message.from_user.id, admin_ids):
        await state.clear()
        return
    price = _number(message.text)
    if price is None or not MIN_STARS_PRICE <= price <= MAX_STARS_PRICE:
        await _screen(message, bot, "<b>Нужно число от 1 до 2500</b>")
        return
    await db.set_setting("price_stars", str(price))
    await state.clear()
    await _screen(message, bot, f"<b>Цена: {price} Stars</b>")


@router.callback_query(F.data == "admin:limit")
async def on_limit(callback: CallbackQuery, state: FSMContext, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    await state.set_state(AdminFlow.awaiting_limit)
    await callback.message.edit_text("<b>Отправь лимит в формате оценки/часы, например 1/24</b>", reply_markup=back_to_menu())
    await callback.answer()


@router.message(AdminFlow.awaiting_limit)
async def on_limit_input(message: Message, state: FSMContext, db, bot, admin_ids):
    if not await _is_admin(message.from_user.id, admin_ids):
        await state.clear()
        return
    parsed = _parse_limit(message.text)
    if parsed is None:
        await _screen(message, bot, "<b>Формат: оценки/часы, например 1/24</b>")
        return
    count, hours = parsed
    await db.set_setting("free_limit_count", str(count))
    await db.set_setting("free_limit_hours", str(hours))
    await state.clear()
    await _screen(message, bot, f"<b>Лимит: {count}/{hours}ч</b>")


@router.callback_query(F.data == "admin:queue")
async def on_queue_size(callback: CallbackQuery, state: FSMContext, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    await state.set_state(AdminFlow.awaiting_queue_size)
    await callback.message.edit_text("<b>Отправь размер очереди на анализ</b>", reply_markup=back_to_menu())
    await callback.answer()


@router.message(AdminFlow.awaiting_queue_size)
async def on_queue_size_input(message: Message, state: FSMContext, db, bot, admin_ids):
    if not await _is_admin(message.from_user.id, admin_ids):
        await state.clear()
        return
    size = _number(message.text)
    if size is None or not MIN_QUEUE_SIZE <= size <= MAX_QUEUE_SIZE:
        await _screen(message, bot, f"<b>Нужно число от {MIN_QUEUE_SIZE} до {MAX_QUEUE_SIZE}</b>")
        return
    await db.set_setting("queue_size", str(size))
    await state.clear()
    await _screen(message, bot, f"<b>Очередь: {size}</b>")


@router.callback_query(F.data.startswith("admin:mode:"))
async def on_toggle_mode(callback: CallbackQuery, db, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    parts = callback.data.split(":")
    if len(parts) != 4 or parts[2] not in MODES or parts[3] not in GENDERS:
        await callback.answer()
        return
    key = mode_key(parts[2], parts[3])
    current = (await db.get_setting(key)) == "1"
    await db.set_setting(key, "0" if current else "1")
    await on_admin(callback, db, admin_ids)


@router.callback_query(F.data == "admin:metrics")
async def on_metrics(callback: CallbackQuery, state: FSMContext, db, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    rows = await db.disabled_metrics_rows(DISABLED_METRICS_PREVIEW)
    await state.set_state(AdminFlow.awaiting_metric_toggle)
    await callback.message.edit_text(_metrics_text(rows), reply_markup=back_to_menu())
    await callback.answer()


@router.message(AdminFlow.awaiting_metric_toggle)
async def on_metric_toggle_input(message: Message, state: FSMContext, db, bot, admin_ids):
    if not await _is_admin(message.from_user.id, admin_ids):
        await state.clear()
        return
    parsed = _parse_metric_toggle(message.text)
    if parsed is None:
        await _screen(message, bot, "<b>Формат: анфас мужской metric_id выкл</b>")
        return
    mode, gender, metric_id, enabled = parsed
    if metric_id not in _metric_ids(mode):
        await _screen(message, bot, "<b>Такого параметра нет</b>")
        return
    await db.set_metric_enabled(mode, gender, metric_id, enabled)
    await state.clear()
    await _screen(message, bot, f"<b>{metric_id}: {'вкл' if enabled else 'выкл'}</b>")


@router.callback_query(F.data == "admin:toggle_paid")
async def on_toggle_paid(callback: CallbackQuery, db, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    current = (await db.get_setting("paid_enabled")) == "1"
    await db.set_setting("paid_enabled", "0" if current else "1")
    await on_admin(callback, db, admin_ids)


@router.callback_query(F.data == "admin:toggle_free")
async def on_toggle_free(callback: CallbackQuery, db, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    current = (await db.get_setting("free_enabled")) == "1"
    await db.set_setting("free_enabled", "0" if current else "1")
    await on_admin(callback, db, admin_ids)


@router.callback_query(F.data == "admin:unlimited")
async def on_unlimited(callback: CallbackQuery, state: FSMContext, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    await state.set_state(AdminFlow.awaiting_unlimited)
    await callback.message.edit_text("<b>Отправь id пользователя и дни через пробел. 0 значит навсегда</b>", reply_markup=back_to_menu())
    await callback.answer()


@router.message(AdminFlow.awaiting_unlimited)
async def on_unlimited_input(message: Message, state: FSMContext, db, bot, admin_ids):
    if not await _is_admin(message.from_user.id, admin_ids):
        await state.clear()
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await _screen(message, bot, "<b>Формат: id дни</b>")
        return
    user_id = int(parts[0])
    days = int(parts[1])
    until = -1 if days == 0 else int(time.time()) + days * 86400
    await db.set_unlimited(user_id, until)
    await state.clear()
    text = "навсегда" if days == 0 else f"{days} дней"
    await _screen(message, bot, f"<b>Безлимит выдан: {user_id}, {text}</b>")


@router.callback_query(F.data == "admin:sponsors")
async def on_sponsors(callback: CallbackQuery, db, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    sponsors = await db.sponsors()
    await callback.message.edit_text(texts.sponsors_list(sponsors), reply_markup=_sponsors_keyboard(sponsors))
    await callback.answer()


@router.callback_query(F.data == "admin:sponsor_add")
async def on_sponsor_add(callback: CallbackQuery, state: FSMContext, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    await state.set_state(AdminFlow.awaiting_sponsor_channel)
    await callback.message.edit_text("<b>Отправь @username или t.me/username канала или группы. Бот должен быть админом</b>", reply_markup=back_to_menu())
    await callback.answer()


@router.message(AdminFlow.awaiting_sponsor_channel)
async def on_sponsor_channel(message: Message, state: FSMContext, db, bot, admin_ids):
    if not await _is_admin(message.from_user.id, admin_ids):
        await state.clear()
        return
    channel = (message.text or "").strip()
    if not valid_sponsor_channel(channel):
        await _screen(message, bot, "<b>Нужен @username или t.me/username публичного канала или группы</b>")
        return
    normalized = normalize_sponsor_channel(channel)
    chat = await _validated_sponsor_chat(bot, normalized)
    if chat is None:
        await _screen(message, bot, "<b>Не могу проверить. Добавь бота админом в канал или группу и отправь username ещё раз</b>")
        return
    channel_id = chat.username or normalized
    title = chat.title or channel_id
    await db.add_sponsor(channel_id, title, 1)
    await state.clear()
    await _screen(message, bot, f"<b>Спонсор добавлен: {title}</b>")


@router.message(AdminFlow.awaiting_sponsor_title)
async def on_sponsor_title(message: Message, state: FSMContext, db, bot, admin_ids):
    await state.clear()
    await _screen(message, bot, "<b>Добавь спонсора через username канала</b>")


@router.callback_query(F.data.startswith("admin:sponsor_del:"))
async def on_sponsor_del(callback: CallbackQuery, db, admin_ids):
    if not await _is_admin(callback.from_user.id, admin_ids):
        await callback.answer()
        return
    sponsor_id = _callback_id(callback.data, 2)
    if sponsor_id is None:
        await callback.answer()
        return
    await db.remove_sponsor(sponsor_id)
    await on_sponsors(callback, db, admin_ids)


async def _validated_sponsor_chat(bot, channel):
    try:
        chat = await bot.get_chat(f"@{channel}")
        me = await bot.get_me()
        member = await bot.get_chat_member(chat.id, me.id)
    except (TelegramBadRequest, TelegramForbiddenError):
        return None
    if member.status not in ("administrator", "creator"):
        return None
    if chat.type not in ("channel", "supergroup", "group"):
        return None
    return chat


def _sponsors_keyboard(sponsors):
    buttons = []
    for sponsor in sponsors:
        buttons.append([
            InlineKeyboardButton(
                text=f"⊘ {sponsor['title']}",
                callback_data=f"admin:sponsor_del:{sponsor['id']}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="⧉ Добавить спонсора", callback_data="admin:sponsor_add")])
    buttons.append([InlineKeyboardButton(text="⭠ Назад", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _callback_id(data, index):
    parts = data.split(":")
    if len(parts) <= index or not parts[index].isdigit():
        return None
    return int(parts[index])


def mode_key(mode, gender):
    return f"{mode}_{gender}_enabled"


async def _mode_states(db):
    states = {}
    for mode in MODES:
        for gender in GENDERS:
            states[f"{mode}_{gender}"] = (await db.get_setting(mode_key(mode, gender))) == "1"
    return states


def _metrics_text(rows):
    lines = [
        "<b>Параметры оценки</b>",
        "<b>Формат: анфас мужской metric_id выкл</b>",
    ]
    if rows:
        lines.append("<b>Выключено:</b>")
        for row in rows:
            mode = "анфас" if row["mode"] == "frontal" else "профиль"
            gender = "мужской" if row["gender"] == "male" else "женский"
            lines.append(f"<b>{mode} {gender}: {row['metric_id']}</b>")
    return "\n".join(lines)


def _parse_metric_toggle(text):
    parts = (text or "").strip().split()
    if len(parts) != 4:
        return None
    mode = MODE_WORDS.get(parts[0].lower())
    gender = GENDER_WORDS.get(parts[1].lower())
    state = STATE_WORDS.get(parts[3].lower())
    if mode is None or gender is None or state is None:
        return None
    return mode, gender, parts[2], state


def _metric_ids(mode):
    return {metric["id"] for metric in load_calibration()["metrics"] if metric["group"] in (mode, "both")}


def _parse_limit(text):
    parts = (text or "").strip().split("/")
    if len(parts) != 2:
        return None
    count = _number(parts[0])
    hours = _number(parts[1])
    if count is None or hours is None:
        return None
    if not MIN_FREE_LIMIT <= count <= MAX_FREE_LIMIT:
        return None
    if not MIN_LIMIT_HOURS <= hours <= MAX_LIMIT_HOURS:
        return None
    return count, hours


def _number(text):
    if text is None:
        return None
    value = text.strip()
    if not value.isdigit():
        return None
    return int(value)
