import json
from datetime import datetime

from engine.calibration import load_advice, load_calibration


def format_value(value, unit):
    if value is None:
        return "н/д"
    if unit in ("ratio", "score"):
        return f"{value:.2f}"
    if unit == "percent":
        return f"{value:.1f}%"
    if unit == "deg":
        return f"{value:.1f}°"
    if unit == "mm":
        return f"{value:.1f} мм"
    return f"{value:.2f}"


def band_text(metric):
    lo, hi = metric["band"]
    return f"{lo:.2f}-{hi:.2f}"


BLOCK_TITLES = {
    "harmony": "ГАРМОНИЯ",
    "misc": "КОЖА И СИММЕТРИЯ",
    "angles": "УГЛЫ ПРОФИЛЯ",
    "dimorphism": "ДИМОРФИЗМ",
}


def build_report(result, gender, bot_username=None):
    lines = []
    lines.append("ОТЧЁТ PSL")
    lines.append("")
    lines.append(f"Ракурс: {'анфас' if result['mode'] == 'frontal' else 'профиль'}")
    lines.append(f"Пол: {'мужской' if gender == 'male' else 'женский'}")
    lines.append(f"PSL: {_score_text(result['psl'])}/10" if result["psl"] is not None else "PSL: не определён")
    version = load_calibration().get("version")
    if version:
        lines.append(f"Калибровка: {version}")
    lines.append("")
    for block, title in BLOCK_TITLES.items():
        block_metrics = [metric for metric in result["metrics"].values() if metric["block"] == block]
        block_value = result.get("blocks", {}).get(block)
        if not block_metrics and block_value is None:
            continue
        lines.append(f"{title}: {_block_text(result, block)}")
        lines.append("")
        if not block_metrics:
            lines.append("  не измерено в этом ракурсе")
            lines.append("")
            continue
        for metric in block_metrics:
            measured = format_value(metric["measured"], metric["unit"])
            lines.append(f"{metric['name_ru']}: {measured}")
            lines.append(f"  норма: {band_text(metric)}")
            lines.append(f"  статус: {_direction(metric)}")
            lines.append(f"  тир: {_tier_text(metric)}")
            lines.append(f"  баллы: {_points_text(metric)}")
            lines.append("")
    defects = _defects(result)
    if defects:
        lines.append("ЧТО ИСПРАВЛЯТЬ")
        lines.append("")
        advice = load_advice()
        for metric in defects:
            lines.append(metric["name_ru"])
            for item in _metric_advice(advice, metric):
                lines.append(f"  ✦ {item}")
            lines.append("")
    if result["warnings"]:
        lines.append("ПРЕДУПРЕЖДЕНИЯ")
        for warning in result["warnings"]:
            lines.append(f"  ⚠ {warning}")
        lines.append("")
    if bot_username:
        lines.append(f"Сделано через @{bot_username}")
    else:
        lines.append("Сделано через бот")
    lines.append(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


def build_json_payload(result):
    return json.dumps(
        {
            "mode": result["mode"],
            "psl": result["psl"],
            "quality": result["quality"],
            "blocks": result.get("blocks", {}),
            "warnings": result["warnings"],
            "pose": result["pose"],
            "lighting": result["lighting"],
            "metrics": {
                k: {
                    "measured": v["measured"],
                    "score": v["score"],
                    "tier": v["tier"],
                    "earned": v["earned"],
                    "direction": v["direction"],
                }
                for k, v in result["metrics"].items()
            },
        },
        ensure_ascii=False,
    )


def _score_text(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _block_text(result, block):
    value = result.get("blocks", {}).get(block)
    return "н/д" if value is None else f"{value:.2f}/10"


def _tier_text(metric):
    return "н/д" if metric["tier"] is None else f"t{metric['tier']}"


def _points_text(metric):
    if metric["earned"] is None:
        return "н/д"
    return f"{metric['earned']:.2f} из {metric['points']:.2f}"


def _direction(metric):
    if metric["measured"] is None:
        return "не измерено"
    return {"low": "ниже нормы", "high": "выше нормы", None: "в норме"}[metric["direction"]]


def _defects(result):
    defects = [
        metric for metric in result["metrics"].values()
        if metric["score"] is not None and metric["direction"] is not None
    ]
    defects.sort(key=lambda metric: (1.0 - metric["score"]) * metric["points"], reverse=True)
    return defects[:8]


def _metric_advice(advice, metric):
    items = advice.get(metric["id"], {}).get(metric["direction"], [])[:2]
    if len(items) >= 2:
        return items
    fallback = [
        "сделай повторный замер на ровном анфас-фото без наклона головы",
        "если отклонение повторяется на разных фото, работай с этой зоной, а не с ракурсом",
    ]
    return (items + fallback)[:2]
