from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.texts import ICON_RATE, ICON_PROFILE, ICON_ADMIN, ICON_BACK, ICON_CANCEL, ICON_DISABLED


def main_menu(is_admin):
    buttons = [
        [InlineKeyboardButton(text=f"{ICON_RATE} Оценка", callback_data="rate")],
        [InlineKeyboardButton(text=f"{ICON_PROFILE} Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="✦ Обратная связь", callback_data="feedback")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text=f"{ICON_ADMIN} Админ", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def gender_menu(male_enabled=True, female_enabled=True):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_option_button("Мужской", "gender", "male", male_enabled)],
            [_option_button("Женский", "gender", "female", female_enabled)],
            [InlineKeyboardButton(text=f"{ICON_BACK} Назад", callback_data="menu")],
        ]
    )


def mode_menu(frontal_enabled=True, profile_enabled=True):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_option_button("Анфас", "mode", "frontal", frontal_enabled)],
            [_option_button("Профиль", "mode", "profile", profile_enabled)],
            [InlineKeyboardButton(text=f"{ICON_BACK} Назад", callback_data="menu")],
        ]
    )


def queue_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"{ICON_CANCEL} Отмена", callback_data="queue_cancel")]]
    )


def _option_button(text, prefix, value, enabled):
    if enabled:
        return InlineKeyboardButton(text=text, callback_data=f"{prefix}:{value}")
    return InlineKeyboardButton(text=f"{text} {ICON_DISABLED}", callback_data=f"{prefix}_disabled:{value}")


def back_to_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"{ICON_BACK} Назад", callback_data="menu")]]
    )


def result_back_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=f"{ICON_BACK} Назад", callback_data="result_back")]]
    )


def profile_history_keyboard(ratings):
    buttons = [
        [
            InlineKeyboardButton(text="Мужской", callback_data="profile_gender:male"),
            InlineKeyboardButton(text="Женский", callback_data="profile_gender:female"),
        ]
    ]
    for rating in ratings:
        psl = _score_text(rating["psl"]) if rating["psl"] is not None else "-"
        marker = "⭐" if rating["paid"] else "◈"
        buttons.append([InlineKeyboardButton(text=f"⊘ {marker} {psl}/10", callback_data=f"rating_del:{rating['id']}")])
    buttons.append([InlineKeyboardButton(text=f"{ICON_BACK} Назад", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def pay_menu(price):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐ Купить оценку · {price}", callback_data="pay")],
            [InlineKeyboardButton(text=f"{ICON_BACK} Назад", callback_data="menu")],
        ]
    )


def admin_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="Цена Stars", callback_data="admin:price")],
            [InlineKeyboardButton(text="Лимит бесплатных", callback_data="admin:limit")],
            [InlineKeyboardButton(text="Безлимит", callback_data="admin:unlimited")],
            [InlineKeyboardButton(text="Платные вкл/выкл", callback_data="admin:toggle_paid")],
            [InlineKeyboardButton(text="Бесплатные вкл/выкл", callback_data="admin:toggle_free")],
            [InlineKeyboardButton(text="Размер очереди", callback_data="admin:queue")],
            [
                InlineKeyboardButton(text="Анфас м", callback_data="admin:mode:frontal:male"),
                InlineKeyboardButton(text="Анфас ж", callback_data="admin:mode:frontal:female"),
            ],
            [
                InlineKeyboardButton(text="Профиль м", callback_data="admin:mode:profile:male"),
                InlineKeyboardButton(text="Профиль ж", callback_data="admin:mode:profile:female"),
            ],
            [InlineKeyboardButton(text="Параметры", callback_data="admin:metrics")],
            [InlineKeyboardButton(text="Спонсоры", callback_data="admin:sponsors")],
            [InlineKeyboardButton(text="Тикеты", callback_data="admin:tickets")],
            [InlineKeyboardButton(text=f"{ICON_BACK} Назад", callback_data="menu")],
        ]
    )


def _score_text(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def sponsors_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить спонсора", callback_data="admin:sponsor_add")],
            [InlineKeyboardButton(text=f"{ICON_BACK} Назад", callback_data="admin")],
        ]
    )
