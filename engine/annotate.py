import io

import numpy as np
from PIL import Image, ImageDraw

from engine.constants import (
    JAW,
    RIGHT_BROW,
    LEFT_BROW,
    NOSE_BRIDGE,
    NOSTRILS,
    RIGHT_EYE,
    LEFT_EYE,
    OUTER_LIP,
    INNER_LIP,
    CHIN,
    NASION,
    NOSE_TIP,
    SUBNASALE,
    BROW_INNER_RIGHT,
    BROW_INNER_LEFT,
)
from engine.geometry import midpoint

POINT_COLOR = (0, 220, 255)
LINE_COLOR = (0, 255, 180)
METRIC_COLOR = (255, 210, 0)
AUX_COLOR = (255, 120, 80)
POINT_RADIUS = 4
LINE_WIDTH = 4
IMAGE_MAX_SIDE = 960
FACE_CROP_MARGIN = 0.42


PAIR_SEGMENTS = {
    "fwhr": [("biz_left", "biz_right"), ("brow_mid", "lip_upper")],
    "tfwhr": [("biz_left", "biz_right"), ("hairline", "chin")],
    "lower_third_ratio": [("subnasale", "chin"), ("hairline", "chin")],
    "midface_ratio": [("pupil_right", "pupil_left"), ("nasion", "lip_upper")],
    "cheekbone_height_ratio": [("cheek_right", "cheek_left"), ("nasion", "subnasale")],
    "lip_ratio": [("lip_upper", "stomion"), ("stomion", "lip_lower")],
    "bigonial_bizygomatic": [("gonion_right", "gonion_left"), ("biz_left", "biz_right")],
    "chin_philtrum": [("lip_lower", "chin"), ("subnasale", "lip_upper")],
    "mouth_nose": [("mouth_right", "mouth_left"), ("nostril_right", "nostril_left")],
    "mouth_aspect_ratio": [("lip_upper", "lip_lower"), ("mouth_right", "mouth_left")],
    "esr": [("pupil_right", "pupil_left"), ("biz_left", "biz_right")],
    "eye_spacing": [("eye_inner_right", "eye_inner_left"), ("eye_outer_right", "eye_inner_right"), ("eye_inner_left", "eye_outer_left")],
    "pfl_pfh": [("eye_outer_right", "eye_inner_right"), ("eye_top_right", "eye_bottom_right"), ("eye_inner_left", "eye_outer_left"), ("eye_top_left", "eye_bottom_left")],
    "canthal_tilt": [("eye_inner_right", "eye_outer_right"), ("eye_inner_left", "eye_outer_left")],
    "medial_canthal_angle": [("eye_top_right", "eye_inner_right"), ("eye_inner_right", "eye_bottom_right"), ("eye_top_left", "eye_inner_left"), ("eye_inner_left", "eye_bottom_left")],
    "eyebrow_position_ratio": [("brow_inner_right", "eye_top_right"), ("brow_inner_left", "eye_top_left")],
    "brow_tilt": [("brow_inner_right", "brow_outer_right"), ("brow_inner_left", "brow_outer_left")],
    "jfa_angle": [("gonion_right", "chin"), ("gonion_left", "chin")],
    "iaa_angle": [("eye_outer_right", "subnasale"), ("eye_outer_left", "subnasale")],
    "iaa_jfa_deviation": [("eye_outer_right", "subnasale"), ("eye_outer_left", "subnasale"), ("gonion_right", "chin"), ("gonion_left", "chin")],
    "symmetry": [("biz_left", "biz_right"), ("nasion", "chin")],
    "dimorphism": [("gonion_right", "gonion_left"), ("biz_left", "biz_right")],
    "skin": [],
}

PROFILE_SEGMENTS = {
    "nasofrontal_angle": [("glabella", "nasion"), ("nasion", "pronasale")],
    "nasolabial_angle": [("pronasale", "subnasale"), ("subnasale", "upper_lip")],
    "facial_convexity": [("glabella", "subnasale"), ("subnasale", "pogonion")],
    "total_convexity": [("glabella", "pronasale"), ("pronasale", "pogonion")],
    "nasomental_angle": [("nasion", "pronasale"), ("pronasale", "pogonion")],
    "nasofacial_angle": [("pogonion", "nasion"), ("nasion", "pronasale")],
    "mentolabial_angle": [("lower_lip", "labiomental"), ("labiomental", "pogonion")],
    "cervicomental_angle": [("pogonion", "cervical"), ("cervical", "neck_lower")],
    "nasal_tip_angle": [("nasion", "pronasale"), ("pronasale", "subnasale")],
    "nasal_projection": [("nasion", "pogonion"), ("pronasale", "nasal_projection_foot")],
    "eline_upper": [("pronasale", "pogonion"), ("upper_lip", "eline_upper_foot")],
    "eline_lower": [("pronasale", "pogonion"), ("lower_lip", "eline_lower_foot")],
    "gonial_angle": [("gonion", "chin")],
}


def anchors(landmarks):
    if landmarks is None:
        return {}
    eye_center_right = np.mean(landmarks[RIGHT_EYE], axis=0)
    eye_center_left = np.mean(landmarks[LEFT_EYE], axis=0)
    return {
        "chin": landmarks[CHIN],
        "chin_right": landmarks[6],
        "chin_left": landmarks[10],
        "nasion": landmarks[NASION],
        "glabella": midpoint(landmarks[BROW_INNER_RIGHT], landmarks[BROW_INNER_LEFT]),
        "nose_tip": landmarks[NOSE_TIP],
        "subnasale": landmarks[SUBNASALE],
        "stomion": midpoint(landmarks[62], landmarks[66]),
        "biz_left": landmarks[0],
        "biz_right": landmarks[16],
        "gonion_right": landmarks[3],
        "gonion_left": landmarks[13],
        "jaw_mid_right": landmarks[1],
        "jaw_low_right": landmarks[5],
        "jaw_mid_left": landmarks[15],
        "jaw_low_left": landmarks[11],
        "eye_outer_right": landmarks[36],
        "eye_inner_right": landmarks[39],
        "eye_inner_left": landmarks[42],
        "eye_outer_left": landmarks[45],
        "eye_top_right": midpoint(landmarks[37], landmarks[38]),
        "eye_bottom_right": midpoint(landmarks[40], landmarks[41]),
        "eye_top_left": midpoint(landmarks[43], landmarks[44]),
        "eye_bottom_left": midpoint(landmarks[46], landmarks[47]),
        "mouth_right": landmarks[48],
        "mouth_left": landmarks[54],
        "lip_upper": landmarks[51],
        "lip_lower": landmarks[57],
        "nostril_right": landmarks[31],
        "nostril_left": landmarks[35],
        "pupil_right": eye_center_right,
        "pupil_left": eye_center_left,
        "pupil_mid": midpoint(eye_center_right, eye_center_left),
        "brow_mid": midpoint(landmarks[19], landmarks[24]),
        "cheek_right": landmarks[1],
        "cheek_left": landmarks[15],
        "brow_inner_right": landmarks[21],
        "brow_outer_right": landmarks[17],
        "brow_inner_left": landmarks[22],
        "brow_outer_left": landmarks[26],
    }


def draw_face_overlay(image_rgb, landmarks):
    canvas = Image.fromarray(image_rgb).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    if landmarks is None:
        return np.asarray(canvas)
    points = landmarks.astype(np.int32)
    for point in points:
        _point(draw, point, POINT_COLOR)
    for group in (JAW, RIGHT_BROW, LEFT_BROW, NOSE_BRIDGE, NOSTRILS, RIGHT_EYE, LEFT_EYE, OUTER_LIP, INNER_LIP):
        _polyline(draw, points[group], LINE_COLOR, 1)
    return np.asarray(canvas)


def metric_has_overlay(metric_id, result):
    if result.get("landmarks") is not None:
        points = anchors(result.get("landmarks"))
        if result.get("hairline") is not None:
            points["hairline"] = result.get("hairline")
        return _pairs_have_points(points, PAIR_SEGMENTS.get(metric_id, []))
    if result.get("profile_points") is not None and result.get("contour") is not None:
        points = dict(result.get("profile_points"))
        points.update(_profile_projection_points(points))
        return _pairs_have_points(points, PROFILE_SEGMENTS.get(metric_id, []))
    return False


def draw_metric_overlay(image_rgb, metric_id, landmarks, profile_points, contour, hairline):
    canvas = Image.fromarray(image_rgb).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    if landmarks is not None:
        points = anchors(landmarks)
        if hairline is not None:
            points["hairline"] = hairline
        _draw_pairs(draw, points, PAIR_SEGMENTS.get(metric_id, []))
    elif profile_points is not None and contour is not None:
        _contour(draw, contour)
        points = dict(profile_points)
        points.update(_profile_projection_points(points))
        _draw_pairs(draw, points, PROFILE_SEGMENTS.get(metric_id, []))
    return np.asarray(canvas)


def build_summary_image(image_rgb, result, metric_ids):
    image_rgb, result = _fit_image_data(image_rgb, result)
    image_rgb, result = _crop_face_data(image_rgb, result)
    canvas = Image.fromarray(image_rgb).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    if result.get("landmarks") is not None:
        points = anchors(result.get("landmarks"))
        if result.get("hairline") is not None:
            points["hairline"] = result.get("hairline")
        pairs = _unique_pairs(metric_ids, PAIR_SEGMENTS)
        _draw_pairs(draw, points, pairs)
    elif result.get("profile_points") is not None and result.get("contour") is not None:
        _contour(draw, result.get("contour"))
        points = dict(result.get("profile_points"))
        points.update(_profile_projection_points(points))
        pairs = _unique_pairs(metric_ids, PROFILE_SEGMENTS)
        _draw_pairs(draw, points, pairs)
    return _encode_jpeg(np.asarray(canvas))


def _fit_image_data(image_rgb, result):
    height, width = image_rgb.shape[:2]
    longest = max(height, width)
    if longest <= IMAGE_MAX_SIDE:
        return image_rgb, result
    scale = IMAGE_MAX_SIDE / float(longest)
    resized = Image.fromarray(image_rgb).resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.LANCZOS)
    fitted = dict(result)
    fitted["landmarks"] = _scale_array(result.get("landmarks"), scale)
    fitted["contour"] = _scale_array(result.get("contour"), scale)
    fitted["hairline"] = _scale_array(result.get("hairline"), scale)
    fitted["profile_points"] = _scale_points(result.get("profile_points"), scale)
    return np.asarray(resized), fitted


def _scale_array(value, scale):
    if value is None:
        return None
    return np.asarray(value, dtype=np.float64) * scale


def _scale_points(points, scale):
    if points is None:
        return None
    return {key: _scale_array(value, scale) for key, value in points.items()}


def _unique_pairs(metric_ids, mapping):
    pairs = []
    seen = set()
    for metric_id in metric_ids:
        for pair in mapping.get(metric_id, []):
            if pair in seen:
                continue
            seen.add(pair)
            pairs.append(pair)
    return pairs


def _crop_face_data(image_rgb, result):
    box = _content_box(result)
    if box is None:
        return image_rgb, result
    height, width = image_rgb.shape[:2]
    x1, y1, x2, y2 = box
    crop_w = max(1.0, x2 - x1)
    crop_h = max(1.0, y2 - y1)
    margin = max(crop_w, crop_h) * FACE_CROP_MARGIN
    left = max(0, int(np.floor(x1 - margin)))
    top = max(0, int(np.floor(y1 - margin)))
    right = min(width, int(np.ceil(x2 + margin)))
    bottom = min(height, int(np.ceil(y2 + margin)))
    if right <= left or bottom <= top:
        return image_rgb, result
    cropped = image_rgb[top:bottom, left:right].copy()
    shifted = dict(result)
    offset = np.array([left, top], dtype=np.float64)
    shifted["landmarks"] = _shift_array(result.get("landmarks"), offset)
    shifted["contour"] = _shift_array(result.get("contour"), offset)
    shifted["hairline"] = _shift_array(result.get("hairline"), offset)
    shifted["profile_points"] = _shift_points(result.get("profile_points"), offset)
    return cropped, shifted


def _content_box(result):
    arrays = []
    for key in ("landmarks", "contour"):
        value = result.get(key)
        if value is not None:
            arrays.append(np.asarray(value, dtype=np.float64))
    if result.get("hairline") is not None:
        arrays.append(np.asarray([result.get("hairline")], dtype=np.float64))
    profile_points = result.get("profile_points")
    if profile_points is not None:
        arrays.extend(np.asarray([point], dtype=np.float64) for point in profile_points.values() if point is not None)
    if not arrays:
        return None
    points = np.vstack(arrays)
    x1, y1 = np.min(points, axis=0)
    x2, y2 = np.max(points, axis=0)
    return x1, y1, x2, y2


def _shift_array(value, offset):
    if value is None:
        return None
    return np.asarray(value, dtype=np.float64) - offset


def _shift_points(points, offset):
    if points is None:
        return None
    return {key: _shift_array(value, offset) for key, value in points.items()}


def _pairs_have_points(points, pairs):
    if not pairs:
        return False
    for start_key, end_key in pairs:
        if points.get(start_key) is None or points.get(end_key) is None:
            return False
    return True


def _draw_pairs(draw, points, pairs):
    for start_key, end_key in pairs:
        start = points.get(start_key)
        end = points.get(end_key)
        if start is None or end is None:
            continue
        _line(draw, start, end, METRIC_COLOR, LINE_WIDTH)
        _point(draw, start, AUX_COLOR)
        _point(draw, end, AUX_COLOR)


def _profile_projection_points(points):
    result = {}
    nasion = points.get("nasion")
    pronasale = points.get("pronasale")
    pogonion = points.get("pogonion")
    upper_lip = points.get("upper_lip")
    lower_lip = points.get("lower_lip")
    if nasion is not None and pronasale is not None and pogonion is not None:
        result["nasal_projection_foot"] = _projection(pronasale, nasion, pogonion)
    if pronasale is not None and pogonion is not None:
        if upper_lip is not None:
            result["eline_upper_foot"] = _projection(upper_lip, pronasale, pogonion)
        if lower_lip is not None:
            result["eline_lower_foot"] = _projection(lower_lip, pronasale, pogonion)
    return result


def _projection(point, a, b):
    point = np.asarray(point, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    ab = b - a
    denom = float(np.dot(ab, ab))
    if denom == 0.0:
        return a
    return a + ab * float(np.dot(point - a, ab) / denom)


def _line(draw, a, b, color, width):
    draw.line([_xy(a), _xy(b)], fill=color, width=width)


def _point(draw, point, color):
    x, y = _xy(point)
    draw.ellipse([x - POINT_RADIUS, y - POINT_RADIUS, x + POINT_RADIUS, y + POINT_RADIUS], fill=color)


def _xy(point):
    point = np.asarray(point, dtype=np.float64)
    return int(round(point[0])), int(round(point[1]))


def _polyline(draw, points, color, width):
    draw.line([_xy(p) for p in points], fill=color, width=width)


def _contour(draw, contour):
    points = [_xy(p) for p in contour]
    if len(points) > 1:
        draw.line(points, fill=LINE_COLOR, width=2)


def _encode_jpeg(frame_rgb):
    buffer = io.BytesIO()
    Image.fromarray(frame_rgb).save(buffer, format="JPEG", quality=88, optimize=True)
    buffer.seek(0)
    return buffer.getvalue()
