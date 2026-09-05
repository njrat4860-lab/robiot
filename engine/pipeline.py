import gc

import numpy as np
from engine import imageio
from engine import landmarks as lm
from engine.calibration import load_calibration, metric_lookup
from engine.hairline import estimate as estimate_hairline
from engine.lighting import analyze as analyze_lighting, assess as assess_lighting
from engine.metrics.frontal import compute_frontal
from engine.metrics.profile import compute_profile, extract_landmarks as extract_profile_landmarks
from engine.metrics.skin import compute_skin_score
from engine.models import ensure_models, predictor_path, mmod_path
from engine.pose import estimate_pose_with_matrix, normalize_landmarks, normalize_points, is_frontal, pose_warnings, detect_emotion_warnings, emotion_metrics
from engine.score import aggregate, deviation_direction

_ENGINE = None
PROFILE_FRONTAL_YAW_LIMIT = 18.0
PROFILE_FRONTAL_ROLL_LIMIT = 18.0
EMOTION_REJECT_EAR = 0.16
EMOTION_REJECT_MAR = 0.50
ANALYZE_MAX_SIDE = 640


def _engine():
    global _ENGINE
    if _ENGINE is None:
        ensure_models()
        _ENGINE = lm.LandmarkEngine(predictor_path(), mmod_path())
    return _ENGINE


def analyze(image_rgb, gender, mode="frontal", disabled_metrics=None):
    calibration = load_calibration()
    disabled = frozenset(disabled_metrics or ())
    image_rgb = imageio.resize_longest_side(image_rgb, ANALYZE_MAX_SIDE, resample="bilinear")
    if mode == "frontal":
        result = _analyze_frontal(image_rgb, gender, calibration, disabled)
    else:
        result = _analyze_profile(image_rgb, gender, calibration, disabled)
    gc.collect()
    return result


def _analyze_frontal(image_rgb, gender, calibration, disabled_metrics):
    engine = _engine()
    gray = imageio.to_gray(image_rgb)
    lighting = analyze_lighting(gray)
    light_problems = assess_lighting(lighting, calibration["lighting"])
    del gray

    image_rgb, landmarks, box, rotation_warning = _detect_frontal_with_rotation(engine, image_rgb)
    if landmarks is None:
        return _empty_result("frontal", gender, ["лицо не найдено - сфотографируй анфас крупным планом"])

    yaw, pitch, roll, rotation_matrix = estimate_pose_with_matrix(landmarks, image_rgb.shape)
    limits = calibration["pose"]
    if not is_frontal(yaw, pitch, roll, limits):
        return _empty_result(
            "frontal",
            gender,
            ["это не анфас - повернись к камере прямо, либо выбери режим профиля"],
        )

    emotion_warn = detect_emotion_warnings(landmarks)
    emo_metrics = emotion_metrics(landmarks)
    if emo_metrics.get("eye_aspect") is not None and emo_metrics["eye_aspect"] < EMOTION_REJECT_EAR:
        return _empty_result("frontal", gender, emotion_warn or ["глаза закрыты - открой глаза"])
    if emo_metrics.get("mouth_aspect") is not None and emo_metrics["mouth_aspect"] > EMOTION_REJECT_MAR:
        return _empty_result("frontal", gender, emotion_warn or ["рот открыт - сделай нейтральное лицо"])

    hairline, hair_warning = estimate_hairline(image_rgb, landmarks, box[1])
    measured_hairline = None
    if hair_warning is None:
        measured_hairline = normalize_points([hairline], landmarks, yaw, pitch, roll, rotation_matrix)[0]
    normalized = normalize_landmarks(landmarks, yaw, pitch, roll, rotation_matrix)

    values = compute_frontal(normalized, measured_hairline, image_rgb, gender, landmarks)
    values["skin"] = compute_skin_score(image_rgb, landmarks)

    warnings = pose_warnings(yaw, pitch, roll, limits) + light_problems + emotion_warn
    if rotation_warning:
        warnings.append(rotation_warning)
    if hair_warning:
        warnings.append(hair_warning)
    if values.get("brow_tilt") is None:
        warnings.append("зона бровей закрыта или распознана ненадёжно - связанные метрики не начислены")
    if values.get("esr") is None or values.get("bigonial_bizygomatic") is None:
        warnings.append("лицо повернуто или есть перспектива - ширинные метрики не начислены")

    result = aggregate(values, "frontal", gender, disabled_metrics)
    return _build_result("frontal", gender, values, result, warnings, {
        "yaw": yaw, "pitch": pitch, "roll": roll,
        "eye_aspect": emo_metrics.get("eye_aspect"),
        "mouth_aspect": emo_metrics.get("mouth_aspect"),
        "smile_ratio": emo_metrics.get("smile_ratio"),
    }, lighting, landmarks=landmarks, image=image_rgb, hairline=None if hair_warning else hairline)


def _detect_frontal_with_rotation(engine, image_rgb):
    landmarks, box = engine.detect_frontal(image_rgb)
    if landmarks is not None:
        return image_rgb, landmarks, box, None
    for turns in (1, 2, 3):
        candidate = np.ascontiguousarray(np.rot90(image_rgb, turns))
        landmarks, box = engine.detect_frontal(candidate)
        if landmarks is not None:
            return candidate, landmarks, box, "фото повёрнуто автоматически"
    return image_rgb, None, None, None


def _analyze_profile(image_rgb, gender, calibration, disabled_metrics):
    engine = _engine()
    gray = imageio.to_gray(image_rgb)
    lighting = analyze_lighting(gray)
    light_problems = assess_lighting(lighting, calibration["lighting"])
    del gray

    frontal_landmarks, frontal_box = engine.detect_frontal(image_rgb)
    if _looks_like_frontal(frontal_landmarks, image_rgb.shape):
        return _empty_result("profile", gender, ["это анфас - выбери режим анфас"])

    box = frontal_box if frontal_box is not None else engine.detect_face_box(image_rgb)
    if box is None:
        return _empty_result("profile", gender, ["лицо не найдено - сфотографируй строго в профиль"])

    contour, profile_landmarks = _detect_profile(image_rgb, box)
    if profile_landmarks is None:
        return _empty_result("profile", gender, ["профиль не распознан - нужен чёткий контур лица на контрастном фоне"])

    values = compute_profile(profile_landmarks, contour)
    warnings = light_problems + ["профиль измеряется по контуру - надёжность ниже, чем у анфаса"]

    result = aggregate(values, "profile", gender, disabled_metrics)
    return _build_result("profile", gender, values, result, warnings, {}, lighting,
                         landmarks=None, contour=contour, profile_points=profile_landmarks, image=image_rgb)


def _looks_like_frontal(landmarks, image_shape):
    if landmarks is None:
        return False
    try:
        yaw, _, roll, _ = estimate_pose_with_matrix(landmarks, image_shape)
    except Exception:
        return False
    return abs(yaw) <= PROFILE_FRONTAL_YAW_LIMIT and abs(roll) <= PROFILE_FRONTAL_ROLL_LIMIT


def _detect_profile(image_rgb, box):
    for facing in ("right", "left"):
        contour = lm.extract_profile_silhouette(image_rgb, box, facing)
        if contour is None:
            continue
        profile_landmarks = extract_profile_landmarks(contour, facing)
        if profile_landmarks is not None:
            return contour, profile_landmarks
    return None, None


def _empty_result(mode, gender, warnings):
    return {
        "mode": mode,
        "gender": gender,
        "psl": None,
        "quality": None,
        "blocks": {},
        "metrics": {},
        "warnings": warnings,
        "pose": {},
        "lighting": {},
        "landmarks": None,
        "contour": None,
        "profile_points": None,
        "hairline": None,
        "image": None,
    }


def _build_result(mode, gender, values, aggregate_result, warnings, pose, lighting, landmarks=None, contour=None, profile_points=None, image=None, hairline=None):
    lookup = metric_lookup(load_calibration())
    metrics = {}
    for metric_id, entry in aggregate_result["results"].items():
        metric = lookup.get(metric_id)
        if metric is None:
            continue
        metrics[metric_id] = {
            "id": metric_id,
            "measured": entry["measured"],
            "score": entry["score"],
            "name_ru": metric["name_ru"],
            "unit": metric["unit"],
            "band": metric["band"][gender],
            "ideal": metric["ideal"][gender],
            "points": metric["points"],
            "block": metric["block"],
            "tier": entry["tier"],
            "earned": entry["points"],
            "direction": deviation_direction(entry["measured"], metric, gender),
        }
    return {
        "mode": mode,
        "gender": gender,
        "psl": aggregate_result["psl"],
        "quality": aggregate_result["quality"],
        "blocks": aggregate_result.get("blocks", {}),
        "metrics": metrics,
        "warnings": warnings,
        "pose": pose,
        "lighting": lighting,
        "landmarks": landmarks,
        "contour": contour,
        "profile_points": profile_points,
        "hairline": hairline,
        "image": image,
    }
