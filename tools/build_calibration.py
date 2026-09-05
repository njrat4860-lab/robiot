import json
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
CALIBRATION_FILE = ASSETS / "calibration.json"
VERSION = 6.4

GUIDE = "looksmax.gg full measuring guide 13427"
GREYCELS = "looksmax.org ideal ratios for men 1153183 (CreatingAttractive)"
CARD = "карточка замеров Чико"
PSLSCALE = "pslscale.net psl rating for women"
POWELL = "Powell, Humphreys via Leong, White 2006"
LEGAN = "Legan, Burstone 1980"
ARNETT = "Arnett, Bergman via Riveiro 2010"
CROATIAN = "Anic-Milosevic 2008, soft tissue profile angular analysis"
UZUN = "Uzun 2014, Turkish adults"
NO_FEMALE_BAND = "женская полоса в источниках не найдена, взята мужская"
NO_BAND = "полоса в источниках не найдена"
CARD_CALIBRATION = "поправка разметки dlib выведена из ручных замеров карточки Чико, одна точка калибровки"

HAIRLINE_CORRECTION = 1.11

LANDMARK_CORRECTIONS = {
    "esr": {"scale": 1.021},
    "canthal_tilt": {"offset": 4.5},
    "jfa_angle": {"offset": -5.4},
    "fwhr": {"scale": 1.06},
    "cheekbone_height_ratio": {"scale": 1.19},
    "chin_philtrum": {"scale": 0.8},
    "lip_ratio": {"scale": 0.85},
    "mouth_nose": {"scale": 0.715},
    "pfl_pfh": {"scale": 0.95},
    "eye_spacing": {"scale": 0.65},
    "eyebrow_position_ratio": {"scale": 0.28},
    "brow_tilt": {"offset": 9.5},
}

HARMONY = "harmony"
MISC = "misc"
DIMORPHISM = "dimorphism"
ANGLES = "angles"

FRONTAL_METRICS = [
    ("esr", "ESR (межзрачковое к ширине лица)", "ratio", (0.443, 0.473), (0.443, 0.473), 35.0, GUIDE),
    ("canthal_tilt", "Кантальный наклон", "deg", (5.0, 9.0), (4.0, 8.0), 25.0, GUIDE + " / " + PSLSCALE),
    ("fwhr", "FWHR (ширина к верхней высоте)", "ratio", (1.9, 2.06), (1.75, 1.9), 25.0, GUIDE + " / " + PSLSCALE),
    ("jfa_angle", "Челюстной фронтальный угол", "deg", (84.5, 95.0), (84.5, 95.0), 25.0, GUIDE + "; " + NO_FEMALE_BAND),
    ("cheekbone_height_ratio", "Высота скул", "ratio", (0.81, 1.0), (0.81, 1.0), 20.0, GUIDE),
    ("tfwhr", "tFWHR (ширина к полной высоте)", "ratio", (1.33, 1.38), (1.33, 1.38), 15.0, GUIDE + "; " + NO_FEMALE_BAND),
    ("bigonial_bizygomatic", "Бигониальная к скуловой", "ratio", (0.855, 0.92), (0.855, 0.92), 15.0, GUIDE + "; " + NO_FEMALE_BAND),
    ("chin_philtrum", "Подбородок к фильтруму", "ratio", (2.05, 2.55), (2.05, 2.55), 12.5, GUIDE + "; " + NO_FEMALE_BAND),
    ("mouth_nose", "Ширина рта к ширине носа", "ratio", (1.38, 1.53), (1.38, 1.53), 10.0, GUIDE),
    ("midface_ratio", "Мидфейс (межзрачковое к высоте)", "ratio", (0.95, 1.01), (0.95, 1.01), 10.0, GUIDE),
    ("eyebrow_position_ratio", "Посадка бровей в высотах глаза", "ratio", (0.0, 0.66), (0.0, 0.66), 10.0, GREYCELS + "; " + NO_FEMALE_BAND),
    ("eye_spacing", "Расстояние между глазами", "ratio", (0.93, 1.04), (0.93, 1.04), 10.0, GUIDE),
    ("pfl_pfh", "Форма глаза (длина к высоте)", "ratio", (3.0, 3.5), (3.0, 3.5), 10.0, GUIDE),
    ("medial_canthal_angle", "Медиальный кантальный угол", "deg", (20.0, 42.0), (20.0, 42.0), 10.0, GUIDE),
    ("mouth_aspect_ratio", "Высота рта к ширине", "ratio", (0.32, 0.52), (0.32, 0.54), 10.0, CARD + "; " + NO_BAND),
    ("lip_ratio", "Нижняя губа к верхней", "ratio", (1.4, 2.0), (1.4, 2.0), 7.5, GUIDE),
    ("iaa_jfa_deviation", "Отклонение IAA от JFA", "deg", (0.0, 2.5), (0.0, 2.5), 7.0, GUIDE),
    ("brow_tilt", "Наклон бровей", "deg", (5.0, 13.0), (5.0, 13.0), 6.0, GUIDE + "; " + NO_FEMALE_BAND),
    ("lower_third_ratio", "Нижняя треть лица", "ratio", (0.306, 0.34), (0.306, 0.34), 5.0, GUIDE),
    ("iaa_angle", "Ипсилатеральный альярный угол", "deg", (85.0, 95.0), (85.0, 95.0), 2.5, GUIDE),
]

MISC_METRICS = [
    ("skin", "Качество кожи", "percent", (70.0, 100.0), (70.0, 100.0), "engine.metrics.skin, шкала движка"),
    ("symmetry", "Симметрия лица", "percent", (92.0, 100.0), (92.0, 100.0), "engine.metrics.frontal, шкала движка"),
]

DIMORPHISM_METRIC = ("dimorphism", "Половой диморфизм", "percent", (58.0, 98.0), (35.0, 75.0), "engine.metrics.frontal, шкала движка")

PROFILE_METRICS = [
    ("nasofrontal_angle", "Назофронтальный угол", "deg", (115.0, 130.0), (120.0, 140.0), POWELL + " / " + UZUN),
    ("nasolabial_angle", "Назолабиальный угол", "deg", (94.0, 110.0), (100.0, 116.0), LEGAN + " / " + CROATIAN),
    ("nasofacial_angle", "Назофациальный угол", "deg", (30.0, 40.0), (30.0, 40.0), POWELL),
    ("nasomental_angle", "Назоментальный угол", "deg", (120.0, 132.0), (120.0, 132.0), POWELL),
    ("mentolabial_angle", "Ментолабиальный угол", "deg", (108.0, 130.0), (120.0, 140.0), CROATIAN),
    ("facial_convexity", "Выпуклость лица", "deg", (165.0, 175.0), (165.0, 175.0), ARNETT),
    ("total_convexity", "Полная выпуклость лица", "deg", (136.0, 147.0), (136.0, 147.0), LEGAN),
    ("nasal_tip_angle", "Угол кончика носа", "deg", (103.0, 113.0), (104.0, 115.0), GREYCELS),
    ("cervicomental_angle", "Цервикоментальный угол", "deg", (90.0, 110.0), (90.0, 110.0), GREYCELS),
    ("gonial_angle", "Гониальный угол", "deg", (110.0, 122.0), (120.0, 128.0), GREYCELS + " / " + PSLSCALE),
    ("nasal_projection", "Проекция носа", "ratio", (0.55, 0.6), (0.55, 0.6), "Goode ratio"),
    ("eline_upper", "Линия E, верхняя губа", "ratio", (-6.0, -2.0), (-6.0, -2.0), "Ricketts E-line"),
    ("eline_lower", "Линия E, нижняя губа", "ratio", (-4.0, 0.0), (-4.0, 0.0), "Ricketts E-line"),
]

PROFILE_POINTS = 10.0


def band_entry(male, female):
    return {"male": list(male), "female": list(female)}


def ideal_entry(male, female):
    return {"male": round(sum(male) / 2.0, 4), "female": round(sum(female) / 2.0, 4)}


def _with_correction_note(metric_id, source):
    if metric_id in LANDMARK_CORRECTIONS:
        return source + "; " + CARD_CALIBRATION
    return source


def build_metrics():
    metrics = []
    hairline_driven = ("tfwhr", "lower_third_ratio")
    for metric_id, name, unit, male, female, points, source in FRONTAL_METRICS:
        metrics.append({
            "id": metric_id,
            "name_ru": name,
            "group": "frontal",
            "block": HARMONY,
            "shape": "band",
            "unit": unit,
            "points": points,
            "band": band_entry(male, female),
            "ideal": ideal_entry(male, female),
            "source": _with_correction_note(metric_id, source) + (
                "; высота лица от линии волос скорректирована" if metric_id in hairline_driven else ""
            ),
            "landmark_correction": LANDMARK_CORRECTIONS.get(metric_id, {}),
        })
    for metric_id, name, unit, male, female, source in MISC_METRICS:
        metrics.append({
            "id": metric_id,
            "name_ru": name,
            "group": "frontal",
            "block": MISC,
            "shape": "percent",
            "unit": unit,
            "points": PROFILE_POINTS,
            "band": band_entry(male, female),
            "ideal": ideal_entry(male, female),
            "source": source,
            "landmark_correction": {},
        })
    metric_id, name, unit, male, female, source = DIMORPHISM_METRIC
    metrics.append({
        "id": metric_id,
        "name_ru": name,
        "group": "frontal",
        "block": DIMORPHISM,
        "shape": "percent",
        "unit": unit,
        "points": PROFILE_POINTS,
        "band": band_entry(male, female),
        "ideal": ideal_entry(male, female),
        "source": source,
        "landmark_correction": {},
    })
    for metric_id, name, unit, male, female, source in PROFILE_METRICS:
        metrics.append({
            "id": metric_id,
            "name_ru": name,
            "group": "profile",
            "block": ANGLES,
            "shape": "band",
            "unit": unit,
            "points": PROFILE_POINTS,
            "band": band_entry(male, female),
            "ideal": ideal_entry(male, female),
            "source": source,
            "landmark_correction": {},
        })
    return metrics


def build():
    with open(CALIBRATION_FILE, encoding="utf-8") as file:
        current = json.load(file)
    calibration = {
        "version": VERSION,
        "scale": {
            "min": 1.0,
            "max": 10.0,
            "decimals": 2,
            "block_weights": {HARMONY: 0.75, MISC: 0.1, ANGLES: 0.0, DIMORPHISM: 0.15},
            "psl_curve": [[1.0, 1.0], [3.95, 1.9], [5.0, 3.2], [6.0, 5.0], [7.18, 7.82], [8.5, 8.6], [10.0, 9.4]],
            "tier_halving_step": 1.0,
            "hairline_correction": HAIRLINE_CORRECTION,
            "max_tier": 5,
        },
        "pose": current["pose"],
        "lighting": current["lighting"],
        "metrics": build_metrics(),
    }
    with open(CALIBRATION_FILE, "w", encoding="utf-8") as file:
        json.dump(calibration, file, ensure_ascii=False, indent=1)
        file.write("\n")
    return calibration


if __name__ == "__main__":
    built = build()
    print(len(built["metrics"]), "metrics", "version", built["version"])
