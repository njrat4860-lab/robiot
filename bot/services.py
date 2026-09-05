import asyncio

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.texts import ICON_OK
from engine import imageio

TELEGRAM_HOSTS = ("https://t.me/", "http://t.me/", "t.me/")
BUTTON_TEXT_LIMIT = 64


def decode_photo(data):
    return imageio.decode(data)


async def run_analysis(pipeline_analyze, image_rgb, gender, mode, disabled_metrics=None):
    return await asyncio.to_thread(pipeline_analyze, image_rgb, gender, mode, disabled_metrics)


async def check_sponsors(bot, user_id, sponsors):
    unsubscribed = []
    for sponsor in sponsors:
        if not sponsor["required"]:
            continue
        channel_id = _chat_id(sponsor["channel_id"])
        try:
            member = await bot.get_chat_member(channel_id, user_id)
        except Exception:
            unsubscribed.append(sponsor)
            continue
        if member.status not in ("member", "administrator", "creator"):
            unsubscribed.append(sponsor)
    return unsubscribed


def sponsor_keyboard(sponsors):
    buttons = []
    for sponsor in sponsors:
        buttons.append([InlineKeyboardButton(text=_button_text(sponsor["title"]), url=_sponsor_url(sponsor["channel_id"]))])
    buttons.append([InlineKeyboardButton(text=f"{ICON_OK} Проверить подписку", callback_data="sponsor_check")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _chat_id(value):
    value = value.strip()
    for host in TELEGRAM_HOSTS:
        if value.startswith(host):
            value = value[len(host):]
            break
    if value.startswith("+"):
        return value
    if value.startswith("@"):
        return value
    if value.lstrip("-").isdigit():
        return int(value)
    return f"@{value}"


def _sponsor_url(value):
    value = value.strip()
    if value.startswith(("https://t.me/", "http://t.me/")):
        return value
    if value.startswith("t.me/"):
        return f"https://{value}"
    if value.startswith("+"):
        return f"https://t.me/{value}"
    return f"https://t.me/{value.lstrip('@')}"


def _button_text(text):
    text = str(text).strip()
    if len(text) <= BUTTON_TEXT_LIMIT:
        return text
    return text[:BUTTON_TEXT_LIMIT - 1].rstrip() + "…"
