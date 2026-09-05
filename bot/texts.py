from html import escape

ICON_RATE = "◈"
ICON_PROFILE = "⚑"
ICON_ADMIN = "⭓"
ICON_BACK = "⭠"
ICON_OK = "✔"
ICON_WARN = "⚠"
ICON_STAR = "⭐"
ICON_CANCEL = "⊘"
ICON_DISABLED = "✕"
ICON_QUEUE = "⧖"

START = "<b>Оценка внешности по PSL</b>"

MAIN_MENU = "<b>Главное меню</b>"

CHOOSE_GENDER = "<b>Укажи пол человека на фото</b>"

CHOOSE_MODE = "<b>Выбери ракурс</b>"

SEND_PHOTO = "<b>Отправь фото лица крупным планом</b>"

USE_MENU = "<b>Сначала нажми «Оценка» и выбери ракурс</b>"

SPONSOR_REQUIRED = "<b>Подпишись на каналы, чтобы пользоваться ботом</b>"

LIMIT_EXCEEDED = "<b>Лимит бесплатных оценок исчерпан</b>"

ANALYSIS_ERROR = "<b>Фото не удалось обработать</b>"

MODE_UNAVAILABLE = "<b>Этот ракурс сейчас недоступен</b>"

RATING_DISABLED = "<b>Оценки временно недоступны</b>"

QUEUE_FULL = "<b>Очередь заполнена. Попробуй чуть позже</b>"

QUEUE_ALREADY = "<b>Твоё фото уже в очереди</b>"

QUEUE_CANCELLED = "<b>Оценка отменена, запрос не потрачен</b>"

ANALYSIS_STARTED = "<b>Анализирую ◷</b>"

FILE_TOO_LARGE = "<b>Файл слишком большой</b>"


def queue_position(position):
    return f"<b>{ICON_QUEUE} Ты {position} в очереди</b>"


def limit_info(remaining, limit):
    return f"<b>Осталось оценок: {remaining} из {limit}</b>"


def rating_message(result, remaining=None, limit=None):
    psl = _score_text(result["psl"]) if result["psl"] is not None else "-"
    mode = "анфас" if result["mode"] == "frontal" else "профиль"
    lines = [
        f"<b>{ICON_RATE} PSL: {psl}/10</b>",
        f"<b>Ракурс: {mode}</b>",
    ]
    for block, title in BLOCK_TITLES.items():
        value = result.get("blocks", {}).get(block)
        if value is not None:
            lines.append(f"<b>{title}: {value:.2f}/10</b>")
    worst = _worst_metrics(result, 3)
    if worst:
        lines.append("<b>Отклонения:</b>")
        for _, metric in worst:
            lines.append(f"<b>✦ {escape(metric['name_ru'])} - {_direction_text(metric['direction'])}</b>")
    if result["warnings"]:
        lines.append(f"<b>{ICON_WARN} {escape(_limit_text(', '.join(result['warnings']), 380))}</b>")
    if remaining is not None and limit is not None:
        lines.append(f"<b>Осталось оценок: {remaining} из {limit}</b>")
    return "\n".join(lines)


BLOCK_TITLES = {
    "harmony": "Гармония",
    "misc": "Кожа и симметрия",
    "angles": "Углы профиля",
    "dimorphism": "Диморфизм",
}


def rating_advice(result, advice_data, top):
    worst = _worst_metrics(result, top)
    if not worst:
        return None
    lines = ["<b>Советы по зонам роста:</b>"]
    for metric_id, metric in worst:
        direction = metric["direction"]
        advices = advice_data.get(metric_id, {}).get(direction, [])
        if advices:
            lines.append(f"<b>{escape(metric['name_ru'])}: {escape(advices[0])}</b>")
    return "\n".join(lines)


def profile_history(ratings, gender=None):
    gender_text = {"male": "мужской", "female": "женский"}.get(gender, "не указан")
    lines = [f"<b>Пол для оценки: {gender_text}</b>"]
    if not ratings:
        lines.append("<b>Оценок пока нет</b>")
        return "\n".join(lines)
    lines.append("<b>Последние оценки:</b>")
    for rating in ratings[:10]:
        mode = "анфас" if rating["mode"] == "frontal" else "профиль"
        psl = _score_text(rating["psl"]) if rating["psl"] is not None else "-"
        lines.append(f"<b>◈ {psl}/10 · {mode}</b>")
    if len(ratings) >= 2:
        delta = (ratings[0]["psl"] or 0) - (ratings[-1]["psl"] or 0)
        arrow = "⭢" if delta > 0 else ("⭠" if delta < 0 else "⊖")
        lines.append(f"<b>Изменение: {arrow} {abs(delta):.2f}</b>")
    return "\n".join(lines)


def admin_menu(paid_enabled, free_enabled, price, free_limit_count, free_limit_hours, queue_size, mode_states):
    lines = [
        "<b>Админ-панель</b>",
        f"<b>Платные оценки: {'вкл' if paid_enabled else 'выкл'}</b>",
        f"<b>Бесплатные оценки: {'вкл' if free_enabled else 'выкл'}</b>",
        f"<b>Цена Stars: {escape(str(price))}</b>",
        f"<b>Лимит бесплатных: {escape(str(free_limit_count))}/{escape(str(free_limit_hours))}ч</b>",
        f"<b>Очередь: {escape(str(queue_size))}</b>",
    ]
    for key, title in MODE_TITLES.items():
        lines.append(f"<b>{title}: {'вкл' if mode_states[key] else 'выкл'}</b>")
    return "\n".join(lines)


MODE_TITLES = {
    "frontal_male": "Анфас мужской",
    "frontal_female": "Анфас женский",
    "profile_male": "Профиль мужской",
    "profile_female": "Профиль женский",
}


def admin_stats(total_users, total_ratings, avg_psl, by_mode):
    lines = [
        "<b>Статистика</b>",
        f"<b>Пользователей: {total_users}</b>",
        f"<b>Оценок всего: {total_ratings}</b>",
        f"<b>Средний PSL: {avg_psl:.2f}/10</b>" if avg_psl else "<b>Средний PSL: -</b>",
    ]
    for mode, count in by_mode:
        name = "анфас" if mode == "frontal" else "профиль"
        lines.append(f"<b>{name}: {count}</b>")
    return "\n".join(lines)


def sponsors_list(sponsors):
    if not sponsors:
        return "<b>Спонсоров нет</b>"
    lines = ["<b>Спонсоры:</b>"]
    for sponsor in sponsors:
        required = ICON_OK if sponsor["required"] else "⊖"
        lines.append(f"<b>{required} {escape(sponsor['title'])}</b>")
    return "\n".join(lines)


def _score_text(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _worst_metrics(result, top):
    scored = [
        (metric_id, metric)
        for metric_id, metric in result["metrics"].items()
        if metric["score"] is not None and metric["direction"] is not None
    ]
    scored.sort(key=lambda item: (1.0 - item[1]["score"]) * item[1]["points"], reverse=True)
    return scored[:top]


def _direction_text(direction):
    return {"low": "ниже идеала", "high": "выше идеала"}.get(direction, direction)


def _limit_text(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"
