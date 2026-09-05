import numpy as np

from engine import imageio
from engine.constants import (
    CHIN,
    NASION,
    SUBNASALE,
    RIGHT_EYE_OUTER,
    RIGHT_EYE_INNER,
    LEFT_EYE_INNER,
    LEFT_EYE_OUTER,
    MOUTH_RIGHT,
    MOUTH_LEFT,
    LIP_UPPER,
    LIP_LOWER,
    STOMION_UPPER,
    STOMION_LOWER,
    NOSTRIL_RIGHT,
    NOSTRIL_LEFT,
    JAW_GONION_RIGHT,
    JAW_GONION_LEFT,
)
from engine.calibration import load_calibration
from engine.geometry import distance, midpoint, angle_degrees, eye_centers

RIGHT_BROW = slice(17, 22)
LEFT_BROW = slice(22, 27)
RIGHT_EYE = slice(36, 42)
LEFT_EYE = slice(42, 48)
CHEEK_RIGHT = 1
CHEEK_LEFT = 15
CHIN_CORNER_RIGHT = 6
CHIN_CORNER_LEFT = 10
MIN_BROW_LENGTH_FACTOR = 0.45
MAX_BROW_LENGTH_FACTOR = 2.2
MIN_BROW_EYE_GAP_FACTOR = 0.35
MAX_BROW_EYE_GAP_FACTOR = 4.0
MIN_EYE_WIDTH_BALANCE = 0.88
PERCENT_SCALE = 100.0
MALE_FWHR_MIN = 1.6
MALE_FWHR_MAX = 2.2
MALE_BIGONIAL_MIN = 0.65
MALE_BIGONIAL_MAX = 0.95
MALE_CHIN_WIDTH_MIN = 0.20
MALE_CHIN_WIDTH_MAX = 0.50
MALE_BROW_GAP_MIN = 0.8
MALE_BROW_GAP_MAX = 3.0
MALE_JAW_ANGLE_MIN_DEG = 75.0
MALE_JAW_ANGLE_MAX_DEG = 120.0
MALE_FWHR_WEIGHT = 0.25
MALE_BIGONIAL_WEIGHT = 0.25
MALE_CHIN_WEIGHT = 0.20
MALE_BROW_WEIGHT = 0.15
MALE_JAW_WEIGHT = 0.15
FEMALE_FWHR_MIN = 1.6
FEMALE_FWHR_MAX = 2.2
FEMALE_BIGONIAL_MIN = 0.65
FEMALE_BIGONIAL_MAX = 0.95
FEMALE_LIP_MIN = 1.1
FEMALE_LIP_MAX = 2.1
FEMALE_TILT_MIN_DEG = -2.0
FEMALE_TILT_MAX_DEG = 8.0
FEMALE_CHIN_WIDTH_MIN = 0.20
FEMALE_CHIN_WIDTH_MAX = 0.50
FEMALE_FWHR_WEIGHT = 0.20
FEMALE_BIGONIAL_WEIGHT = 0.20
FEMALE_LIP_WEIGHT = 0.25
FEMALE_TILT_WEIGHT = 0.20
FEMALE_CHIN_WEIGHT = 0.15


def face_width(landmarks):
    return distance(landmarks[0], landmarks[16])


def bigonial_width(landmarks):
    return distance(landmarks[JAW_GONION_RIGHT], landmarks[JAW_GONION_LEFT])


def interpupillary(landmarks):
    right, left = eye_centers(landmarks)
    return distance(right, left)


def stomion(landmarks):
    return midpoint(landmarks[STOMION_UPPER], landmarks[STOMION_LOWER])


def brow_line(landmarks):
    return midpoint(np.mean(landmarks[RIGHT_BROW], axis=0), np.mean(landmarks[LEFT_BROW], axis=0))


def eye_width_mean(landmarks):
    right = distance(landmarks[RIGHT_EYE_OUTER], landmarks[RIGHT_EYE_INNER])
    left = distance(landmarks[LEFT_EYE_INNER], landmarks[LEFT_EYE_OUTER])
    return (right + left) / 2.0


def eye_height_mean(landmarks):
    right_top = midpoint(landmarks[37], landmarks[38])
    right_bottom = midpoint(landmarks[40], landmarks[41])
    left_top = midpoint(landmarks[43], landmarks[44])
    left_bottom = midpoint(landmarks[46], landmarks[47])
    return (distance(right_top, right_bottom) + distance(left_top, left_bottom)) / 2.0


def compute_frontal(landmarks, hairline, image_rgb=None, gender="male", image_landmarks=None):
    width = face_width(landmarks)
    nasion = landmarks[NASION]
    subnasale = landmarks[SUBNASALE]
    chin = landmarks[CHIN]
    upper_lip = landmarks[LIP_UPPER]
    ipd = interpupillary(landmarks)
    eye_width = eye_width_mean(landmarks)
    eye_height = eye_height_mean(landmarks)
    mouth_width = distance(landmarks[MOUTH_RIGHT], landmarks[MOUTH_LEFT])
    mouth_height = distance(upper_lip, landmarks[LIP_LOWER])
    nose_width = distance(landmarks[NOSTRIL_RIGHT], landmarks[NOSTRIL_LEFT])
    intercanthal = distance(landmarks[RIGHT_EYE_INNER], landmarks[LEFT_EYE_INNER])
    full_height = None if hairline is None else distance(hairline, chin) * _hairline_correction()
    jaw_angle = _triangle_angle(landmarks[JAW_GONION_RIGHT], chin, landmarks[JAW_GONION_LEFT])
    alar_angle = _triangle_angle(landmarks[RIGHT_EYE_OUTER], subnasale, landmarks[LEFT_EYE_OUTER])
    visibility_landmarks = image_landmarks if image_landmarks is not None else landmarks
    brow_visible = _brow_zone_visible(image_rgb, visibility_landmarks, eye_height)
    width_reliable = _width_metrics_reliable(visibility_landmarks)
    reliable_width = width if width_reliable else None

    values = {
        "esr": _ratio(ipd, reliable_width),
        "fwhr": _ratio(reliable_width, distance(brow_line(landmarks), upper_lip)) if brow_visible else None,
        "tfwhr": _ratio(full_height, reliable_width),
        "lower_third_ratio": _ratio(distance(subnasale, chin), full_height),
        "midface_ratio": _ratio(ipd, distance(nasion, upper_lip)),
        "cheekbone_height_ratio": _cheekbone_height_ratio(landmarks, nasion, subnasale),
        "bigonial_bizygomatic": _ratio(bigonial_width(landmarks), reliable_width),
        "chin_philtrum": _ratio(distance(landmarks[LIP_LOWER], chin), distance(subnasale, upper_lip)),
        "mouth_nose": _ratio(mouth_width, nose_width),
        "mouth_aspect_ratio": _ratio(mouth_height, mouth_width),
        "lip_ratio": _lip_ratio(landmarks),
        "eye_spacing": _ratio(intercanthal, eye_width),
        "pfl_pfh": _ratio(eye_width, eye_height),
        "canthal_tilt": _canthal_tilt_mean(landmarks),
        "medial_canthal_angle": _medial_canthal_angle(landmarks),
        "eyebrow_position_ratio": _brow_lid_gap(landmarks, eye_height) if brow_visible else None,
        "brow_tilt": _brow_tilt_value(landmarks, eye_width, eye_height) if brow_visible else None,
        "jfa_angle": jaw_angle,
        "iaa_angle": alar_angle,
        "symmetry": _symmetry_percent(landmarks),
    }
    corrected = _corrected(values)
    corrected["iaa_jfa_deviation"] = _angle_deviation(corrected["iaa_angle"], corrected["jfa_angle"])
    corrected["dimorphism"] = _dimorphism_score(corrected, landmarks, reliable_width, eye_height, gender, brow_visible)
    return corrected


def _hairline_correction():
    return load_calibration()["scale"]["hairline_correction"]


def _corrected(values):
    corrections = {
        metric["id"]: metric.get("landmark_correction") or {}
        for metric in load_calibration()["metrics"]
    }
    for metric_id, value in values.items():
        correction = corrections.get(metric_id)
        if not correction or value is None:
            continue
        values[metric_id] = value * correction.get("scale", 1.0) + correction.get("offset", 0.0)
    return values


def _lip_ratio(landmarks):
    mouth = stomion(landmarks)
    upper = distance(landmarks[LIP_UPPER], mouth)
    lower = distance(mouth, landmarks[LIP_LOWER])
    return _ratio(lower, upper)


def _cheekbone_height_ratio(landmarks, nasion, subnasale):
    midface_height = abs(float(subnasale[1] - nasion[1]))
    cheek = midpoint(landmarks[CHEEK_RIGHT], landmarks[CHEEK_LEFT])
    return _ratio(abs(float(subnasale[1] - cheek[1])), midface_height)


def _canthal_tilt_mean(landmarks):
    right = _canthal_tilt(landmarks[RIGHT_EYE_INNER], landmarks[RIGHT_EYE_OUTER])
    left = _canthal_tilt(landmarks[LEFT_EYE_INNER], landmarks[LEFT_EYE_OUTER])
    return (right + left) / 2.0


def _canthal_tilt(inner, outer):
    horizontal = abs(float(outer[0] - inner[0]))
    vertical = float(inner[1] - outer[1])
    if horizontal == 0.0:
        return 0.0
    return float(np.degrees(np.arctan2(vertical, horizontal)))


def _medial_canthal_angle(landmarks):
    right = angle_degrees(landmarks[38], landmarks[RIGHT_EYE_INNER], landmarks[40])
    left = angle_degrees(landmarks[43], landmarks[LEFT_EYE_INNER], landmarks[47])
    return float((right + left) / 2.0)


def _brow_zone_visible(image_rgb, landmarks, eye_height):
    if image_rgb is None or eye_height <= 0.0:
        return True
    skin = imageio.skin_mask(image_rgb)
    visibility = []
    for start, stop in ((17, 22), (22, 27)):
        brow = landmarks[start:stop]
        x0 = max(0, int(np.floor(brow[:, 0].min() - eye_height * 0.35)))
        x1 = min(skin.shape[1], int(np.ceil(brow[:, 0].max() + eye_height * 0.35)) + 1)
        y0 = max(0, int(np.floor(brow[:, 1].min() - eye_height * 0.75)))
        y1 = min(skin.shape[0], int(np.ceil(brow[:, 1].min() + eye_height * 0.10)) + 1)
        region = skin[y0:y1, x0:x1]
        if region.size == 0:
            return False
        visibility.append(float(region.mean()))
    return float(np.mean(visibility)) >= 0.35


def _width_metrics_reliable(landmarks):
    right = distance(landmarks[RIGHT_EYE_OUTER], landmarks[RIGHT_EYE_INNER])
    left = distance(landmarks[LEFT_EYE_INNER], landmarks[LEFT_EYE_OUTER])
    larger = max(right, left)
    smaller = min(right, left)
    if larger <= 0.0:
        return False
    return smaller / larger >= MIN_EYE_WIDTH_BALANCE


def _brow_eye_gap(landmarks, eye_height):
    if eye_height <= 0.0:
        return None
    right_center, left_center = eye_centers(landmarks)
    right_gap = float(right_center[1] - np.mean(landmarks[RIGHT_BROW, 1]))
    left_gap = float(left_center[1] - np.mean(landmarks[LEFT_BROW, 1]))
    return float(abs((right_gap + left_gap) / 2.0) / eye_height)


def _brow_lid_gap(landmarks, eye_height):
    if eye_height <= 0.0:
        return None
    right_lid = float(np.mean(landmarks[[37, 38], 1]))
    left_lid = float(np.mean(landmarks[[43, 44], 1]))
    right_gap = right_lid - float(np.mean(landmarks[RIGHT_BROW, 1]))
    left_gap = left_lid - float(np.mean(landmarks[LEFT_BROW, 1]))
    return float(abs((right_gap + left_gap) / 2.0) / eye_height)


def _brow_tilt_value(landmarks, eye_width, eye_height):
    sides = (
        (landmarks[21], landmarks[17], np.mean(landmarks[RIGHT_EYE], axis=0)),
        (landmarks[22], landmarks[26], np.mean(landmarks[LEFT_EYE], axis=0)),
    )
    tilts = [
        _canthal_tilt(inner, outer)
        for inner, outer, eye_center in sides
        if _brow_side_reliable(inner, outer, eye_center, eye_width, eye_height)
    ]
    if not tilts:
        return None
    return float(np.mean(tilts))


def _brow_side_reliable(inner, outer, eye_center, eye_width, eye_height):
    if eye_width <= 0.0 or eye_height <= 0.0:
        return True
    length = distance(inner, outer)
    if not eye_width * MIN_BROW_LENGTH_FACTOR <= length <= eye_width * MAX_BROW_LENGTH_FACTOR:
        return False
    gap = abs(float(eye_center[1] - ((inner[1] + outer[1]) / 2.0)))
    return eye_height * MIN_BROW_EYE_GAP_FACTOR <= gap <= eye_height * MAX_BROW_EYE_GAP_FACTOR


def _angle_deviation(first, second):
    if first is None or second is None:
        return None
    return abs(float(first - second))


def _triangle_angle(first, apex, second):
    if distance(first, apex) == 0.0 or distance(second, apex) == 0.0:
        return None
    return float(angle_degrees(first, apex, second))


def _ratio(numerator, denominator):
    if numerator is None or not denominator:
        return None
    return float(numerator / denominator)


def _dimorphism_score(values, landmarks, width, eye_height, gender, brow_visible):
    chin_width = _ratio(distance(landmarks[CHIN_CORNER_RIGHT], landmarks[CHIN_CORNER_LEFT]), width)
    brow_gap = values.get("eyebrow_position_ratio") if brow_visible else None
    if gender == "male":
        parts = (
            (_normalized(values.get("fwhr"), MALE_FWHR_MIN, MALE_FWHR_MAX), MALE_FWHR_WEIGHT),
            (_normalized(values.get("bigonial_bizygomatic"), MALE_BIGONIAL_MIN, MALE_BIGONIAL_MAX), MALE_BIGONIAL_WEIGHT),
            (_normalized(chin_width, MALE_CHIN_WIDTH_MIN, MALE_CHIN_WIDTH_MAX), MALE_CHIN_WEIGHT),
            (_normalized(brow_gap, MALE_BROW_GAP_MAX, MALE_BROW_GAP_MIN), MALE_BROW_WEIGHT),
            (_normalized(values.get("jfa_angle"), MALE_JAW_ANGLE_MAX_DEG, MALE_JAW_ANGLE_MIN_DEG), MALE_JAW_WEIGHT),
        )
    else:
        parts = (
            (_normalized(values.get("fwhr"), FEMALE_FWHR_MAX, FEMALE_FWHR_MIN), FEMALE_FWHR_WEIGHT),
            (_normalized(values.get("bigonial_bizygomatic"), FEMALE_BIGONIAL_MAX, FEMALE_BIGONIAL_MIN), FEMALE_BIGONIAL_WEIGHT),
            (_normalized(values.get("lip_ratio"), FEMALE_LIP_MIN, FEMALE_LIP_MAX), FEMALE_LIP_WEIGHT),
            (_normalized(values.get("canthal_tilt"), FEMALE_TILT_MIN_DEG, FEMALE_TILT_MAX_DEG), FEMALE_TILT_WEIGHT),
            (_normalized(chin_width, FEMALE_CHIN_WIDTH_MAX, FEMALE_CHIN_WIDTH_MIN), FEMALE_CHIN_WEIGHT),
        )
    return _weighted_percent(parts)


def _normalized(value, low, high):
    if value is None or low == high:
        return None
    return float(np.clip((value - low) / (high - low), 0.0, 1.0))


def _weighted_percent(parts):
    measured = [(part, weight) for part, weight in parts if part is not None]
    total = sum(weight for _, weight in measured)
    if total <= 0.0:
        return None
    return float(sum(part * weight for part, weight in measured) / total * PERCENT_SCALE)


MIRROR_MAP = {
    0: 16, 1: 15, 2: 14, 3: 13, 4: 12, 5: 11, 6: 10, 7: 9, 8: 8,
    17: 26, 18: 25, 19: 24, 20: 23, 21: 22,
    36: 45, 37: 44, 38: 43, 39: 42, 40: 47, 41: 46,
    31: 35, 32: 34,
    48: 54, 49: 53, 50: 52, 55: 59, 56: 58,
    60: 64, 61: 63, 65: 67,
}


def _symmetry_percent(landmarks):
    center = landmarks[:, 0].mean()
    reflected = landmarks.copy()
    reflected[:, 0] = 2.0 * center - reflected[:, 0]
    errors = [distance(landmarks[source], reflected[target]) for source, target in MIRROR_MAP.items()]
    rms = float(np.sqrt(np.mean(np.square(errors))))
    scale = distance(landmarks[0], landmarks[16])
    if scale == 0:
        return 100.0
    return float(np.clip(PERCENT_SCALE * (1.0 - rms / scale), 0.0, PERCENT_SCALE))
