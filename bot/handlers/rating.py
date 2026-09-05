import asyncio
import gc
import time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, BufferedInputFile

from bot import texts
from bot.analysis_queue import AnalysisQueue, QUEUE_DUPLICATE, QUEUE_FULL
from bot.cleanup import delete_tracked
from bot.handlers.admin import mode_key
from bot.keyboards import mode_menu, gender_menu, back_to_menu, pay_menu, result_back_menu, queue_menu
from bot.services import decode_photo, run_analysis, check_sponsors, sponsor_keyboard
from bot.states import RatingFlow
from engine.annotate import build_summary_image, metric_has_overlay
from engine.io.export import build_report
from engine.pipeline import analyze

router = Router()

MAX_IMAGE_BYTES = 20 * 1024 * 1024
SECONDS_PER_HOUR = 3600
FLOW_CACHE_SECONDS = 180
ANALYSIS_FRAMES = ("<b>Анализирую ◷</b>", "<b>Анализирую ◐</b>", "<b>Анализирую ◍</b>")
ANALYSIS_FRAME_SECONDS = 0.7

_BOT_USERNAME = None
_FLOW_CACHE = {}
_QUEUE = AnalysisQueue()


@router.callback_query(F.data == "rate")
async def on_rate(callback: CallbackQuery, db, bot, state: FSMContext):
    await state.clear()
    if not await _sponsor_ok(bot, callback.from_user.id, db):
        await _send_screen(callback, bot, texts.SPONSOR_REQUIRED, sponsor_keyboard(await db.sponsors()))
        return
    await db.ensure_user(callback.from_user.id)
    await _send_gender_screen(callback, bot, db)


@router.callback_query(F.data == "sponsor_check")
async def on_sponsor_check(callback: CallbackQuery, db, bot):
    if await _sponsor_ok(bot, callback.from_user.id, db):
        await db.ensure_user(callback.from_user.id)
        await _send_gender_screen(callback, bot, db)
        return
    await _send_screen(callback, bot, texts.SPONSOR_REQUIRED, sponsor_keyboard(await db.sponsors()))


@router.callback_query(F.data.startswith("gender_disabled:"))
async def on_gender_disabled(callback: CallbackQuery, bot):
    await _send_screen(callback, bot, texts.MODE_UNAVAILABLE, back_to_menu())


@router.callback_query(F.data.startswith("mode_disabled:"))
async def on_mode_disabled(callback: CallbackQuery, bot):
    await _send_screen(callback, bot, texts.MODE_UNAVAILABLE, back_to_menu())


@router.callback_query(F.data.startswith("gender:"))
async def on_gender(callback: CallbackQuery, db, bot, state: FSMContext):
    gender = callback.data.split(":", 1)[1]
    if gender not in ("male", "female"):
        await callback.answer()
        return
    await db.set_gender(callback.from_user.id, gender)
    _remember_flow(callback.from_user.id, gender=gender)
    await state.update_data(gender=gender)
    if not await _gender_enabled(db, gender):
        await _send_screen(callback, bot, texts.MODE_UNAVAILABLE, back_to_menu())
        return
    await _send_mode_screen(callback, bot, db, gender)


@router.callback_query(F.data.startswith("mode:"))
async def on_mode(callback: CallbackQuery, state: FSMContext, bot, db):
    mode = callback.data.split(":", 1)[1]
    cached = _cached_flow(callback.from_user.id) or {}
    gender = cached.get("gender") or (await state.get_data()).get("gender")
    if mode not in ("frontal", "profile") or gender not in ("male", "female"):
        await callback.answer()
        return
    if not await _mode_enabled(db, mode, gender):
        await _send_screen(callback, bot, texts.MODE_UNAVAILABLE, back_to_menu())
        return
    _remember_flow(callback.from_user.id, mode=mode)
    await state.set_state(RatingFlow.awaiting_photo)
    await state.update_data(mode=mode, gender=gender)
    await _send_screen(callback, bot, texts.SEND_PHOTO, back_to_menu())


@router.callback_query(F.data == "queue_cancel")
async def on_queue_cancel(callback: CallbackQuery):
    await _QUEUE.cancel(callback.from_user.id)
    await callback.answer()


@router.message(RatingFlow.awaiting_photo, F.photo)
async def on_photo(message: Message, state: FSMContext, db, bot):
    await _process_image(message, state, db, bot, message.photo[-1].file_id, message.photo[-1].file_size)


@router.message(RatingFlow.awaiting_photo, F.document)
async def on_image_document(message: Message, state: FSMContext, db, bot):
    document = message.document
    if document.mime_type is None or not document.mime_type.startswith("image/"):
        await message.answer(texts.SEND_PHOTO)
        return
    await _process_image(message, state, db, bot, document.file_id, document.file_size)


@router.message(RatingFlow.awaiting_photo)
async def on_wrong_content(message: Message):
    await message.answer(texts.SEND_PHOTO)


@router.message(F.photo)
async def on_photo_outside_flow(message: Message, state: FSMContext, db, bot):
    cached = _cached_flow(message.from_user.id)
    if cached and cached.get("mode"):
        await state.set_state(RatingFlow.awaiting_photo)
        await state.update_data(mode=cached.get("mode"), gender=cached.get("gender"))
        await _process_image(message, state, db, bot, message.photo[-1].file_id, message.photo[-1].file_size)
        return
    await message.answer(texts.USE_MENU)


async def _process_image(message: Message, state: FSMContext, db, bot, file_id, file_size):
    data = await state.get_data()
    mode = data.get("mode", "frontal")
    user_id = message.from_user.id

    if file_size is not None and file_size > MAX_IMAGE_BYTES:
        await message.answer(texts.FILE_TOO_LARGE)
        return

    if not await _sponsor_ok(bot, user_id, db):
        await message.answer(texts.SPONSOR_REQUIRED, reply_markup=sponsor_keyboard(await db.sponsors()))
        return

    access = await _resolve_access(db, user_id)
    if access == "pay":
        price = int(await db.get_setting("price_stars"))
        await message.answer(texts.LIMIT_EXCEEDED, reply_markup=pay_menu(price))
        return
    if access == "limit":
        await message.answer(texts.LIMIT_EXCEEDED)
        return
    if access == "off":
        await message.answer(texts.RATING_DISABLED)
        return

    user = await db.ensure_user(user_id)
    gender = data.get("gender") or user["gender"] or "male"
    if not await _mode_enabled(db, mode, gender):
        await message.answer(texts.MODE_UNAVAILABLE, reply_markup=back_to_menu())
        return

    await delete_tracked(bot, message.chat.id, [message.message_id])
    progress = await message.answer(texts.ANALYSIS_STARTED, reply_markup=queue_menu())
    entry = await _QUEUE.enqueue(user_id, await _queue_size(db), _position_notifier(progress))
    if entry == QUEUE_FULL:
        await _replace_progress(progress, texts.QUEUE_FULL)
        return
    if entry == QUEUE_DUPLICATE:
        await _replace_progress(progress, texts.QUEUE_ALREADY)
        return

    position = await _QUEUE.position(user_id)
    if position:
        await _edit(progress, texts.queue_position(position), queue_menu())
    try:
        if not await entry.wait_turn():
            await _replace_progress(progress, texts.QUEUE_CANCELLED)
            return
        await _run_and_reply(message, state, db, bot, file_id, mode, gender, access, progress)
    finally:
        await _QUEUE.release(entry)


async def _run_and_reply(message, state, db, bot, file_id, mode, gender, access, progress):
    user_id = message.from_user.id
    image_rgb = await _download_image(bot, file_id)
    if image_rgb is None:
        await _replace_progress(progress, texts.SEND_PHOTO)
        return

    await _edit(progress, texts.ANALYSIS_STARTED, None)
    animation = asyncio.create_task(_animate_analysis(progress))
    try:
        disabled_metrics = await db.disabled_metrics(mode, gender)
        result = await run_analysis(analyze, image_rgb, gender, mode, disabled_metrics)
    except RuntimeError:
        animation.cancel()
        await _replace_progress(progress, texts.ANALYSIS_ERROR)
        return
    finally:
        animation.cancel()
    await _safe_delete(progress)

    if result["psl"] is None:
        await message.answer(texts.rating_message(result), reply_markup=result_back_menu())
        await _finish_flow(state, user_id, result)
        return

    if not await _consume_access(db, user_id, access):
        await message.answer(texts.LIMIT_EXCEEDED)
        await _finish_flow(state, user_id, result)
        return

    await _send_result(message, bot, result, gender)
    if access != "unlimited":
        await db.add_rating(
            user_id, result["mode"], gender, result["psl"], result["quality"],
            result["metrics"], result["warnings"], 1 if access == "paid" else 0,
        )
    await _finish_flow(state, user_id, result)


async def _send_result(message, bot, result, gender):
    psl_text = texts.rating_message(result)
    if result["image"] is not None:
        overlay = build_summary_image(result["image"], result, _overlay_metric_order(result))
        await message.answer_photo(
            BufferedInputFile(overlay, filename="metrics.jpg"),
            caption=psl_text,
            reply_markup=result_back_menu(),
        )
        del overlay
    else:
        await message.answer(psl_text, reply_markup=result_back_menu())
    report = build_report(result, gender, await _bot_username(bot))
    await message.answer_document(
        BufferedInputFile(report.encode("utf-8"), filename="report.txt"),
        caption="<b>Метрики</b>",
    )


async def _finish_flow(state, user_id, result):
    await state.clear()
    _FLOW_CACHE.pop(user_id, None)
    result.clear()
    gc.collect()


async def _download_image(bot, file_id):
    file = await bot.get_file(file_id)
    if file.file_size is not None and file.file_size > MAX_IMAGE_BYTES:
        return None
    raw = await bot.download_file(file.file_path)
    data = raw.read(MAX_IMAGE_BYTES + 1)
    raw.close()
    image_rgb = decode_photo(data)
    del data
    return image_rgb


def _position_notifier(progress):
    async def notify(position):
        await _edit(progress, texts.queue_position(position), queue_menu())
    return notify


async def _replace_progress(progress, text):
    await _safe_delete(progress)
    await progress.answer(text, reply_markup=back_to_menu())


async def _edit(message, text, markup):
    try:
        await message.edit_text(text, reply_markup=markup)
    except Exception:
        return


async def _animate_analysis(message):
    index = 0
    try:
        while True:
            await asyncio.sleep(ANALYSIS_FRAME_SECONDS)
            index = (index + 1) % len(ANALYSIS_FRAMES)
            try:
                await message.edit_text(ANALYSIS_FRAMES[index])
            except Exception:
                return
    except asyncio.CancelledError:
        return


async def _safe_delete(message):
    try:
        await message.delete()
    except Exception:
        return


async def _send_gender_screen(callback, bot, db):
    male_enabled = await _gender_enabled(db, "male")
    female_enabled = await _gender_enabled(db, "female")
    if not male_enabled and not female_enabled:
        await _send_screen(callback, bot, texts.RATING_DISABLED, back_to_menu())
        return
    await _send_screen(callback, bot, texts.CHOOSE_GENDER, gender_menu(male_enabled, female_enabled))


async def _send_mode_screen(callback, bot, db, gender):
    frontal_enabled = await _mode_enabled(db, "frontal", gender)
    profile_enabled = await _mode_enabled(db, "profile", gender)
    await _send_screen(callback, bot, texts.CHOOSE_MODE, mode_menu(frontal_enabled, profile_enabled))


async def _gender_enabled(db, gender):
    return await _mode_enabled(db, "frontal", gender) or await _mode_enabled(db, "profile", gender)


async def _mode_enabled(db, mode, gender):
    return (await db.get_setting(mode_key(mode, gender))) == "1"


async def _queue_size(db):
    return int(await db.get_setting("queue_size"))


async def _send_screen(callback, bot, text, markup):
    await _QUEUE.cancel(callback.from_user.id)
    await delete_tracked(bot, callback.message.chat.id, [callback.message.message_id])
    await bot.send_message(callback.message.chat.id, text, reply_markup=markup)
    await callback.answer()


async def _sponsor_ok(bot, user_id, db):
    sponsors = await db.sponsors()
    return not await check_sponsors(bot, user_id, sponsors)


async def _resolve_access(db, user_id):
    if await db.has_unlimited(user_id):
        return "unlimited"
    free_enabled = (await db.get_setting("free_enabled")) == "1"
    paid_enabled = (await db.get_setting("paid_enabled")) == "1"
    count, hours = await db.free_limit()
    if free_enabled and await db.free_remaining(user_id, count, hours * SECONDS_PER_HOUR) > 0:
        return "free"
    if paid_enabled:
        if await db.paid_credits(user_id) > 0:
            return "paid"
        return "pay"
    if free_enabled:
        return "limit"
    return "off"


async def _consume_access(db, user_id, access):
    if access == "free":
        count, hours = await db.free_limit()
        return await db.consume_free_rating(user_id, count, hours * SECONDS_PER_HOUR)
    if access == "paid":
        return await db.consume_credit(user_id)
    return True


def _remember_flow(user_id, gender=None, mode=None):
    cached = _FLOW_CACHE.get(user_id, {})
    if gender is not None:
        cached["gender"] = gender
    if mode is not None:
        cached["mode"] = mode
    cached["time"] = time.monotonic()
    _FLOW_CACHE[user_id] = cached
    return cached


def _cached_flow(user_id):
    cached = _FLOW_CACHE.get(user_id)
    if not cached:
        return None
    if time.monotonic() - cached.get("time", 0.0) > FLOW_CACHE_SECONDS:
        _FLOW_CACHE.pop(user_id, None)
        return None
    return cached


async def _bot_username(bot):
    global _BOT_USERNAME
    if _BOT_USERNAME is not None:
        return _BOT_USERNAME
    me = await bot.get_me()
    _BOT_USERNAME = me.username or ""
    return _BOT_USERNAME


async def cancel_queued(user_id):
    return await _QUEUE.cancel(user_id)


def _overlay_metric_order(result):
    scored = [
        (metric_id, metric)
        for metric_id, metric in result["metrics"].items()
        if metric["score"] is not None and metric_id != "skin" and metric_has_overlay(metric_id, result)
    ]
    problem_metrics = [item for item in scored if item[1]["direction"] is not None]
    stable_metrics = [item for item in scored if item[1]["direction"] is None]
    problem_metrics.sort(key=lambda item: (1.0 - item[1]["score"]) * item[1]["points"], reverse=True)
    stable_metrics.sort(key=lambda item: item[1]["points"], reverse=True)
    return [metric_id for metric_id, _ in problem_metrics + stable_metrics]
