import numpy as np

from engine.geometry import distance, angle_degrees

NOSE_MM_NOMINAL = 48.0


def _band(contour, y0, y1, key):
    rows = [p for p in contour if y0 <= p[1] <= y1]
    if not rows:
        return None
    return rows[int(np.argmax([key(p) for p in rows]))]


def _smooth(contour, window):
    xs = contour[:, 0].astype(np.float64)
    ys = contour[:, 1].astype(np.float64)
    if len(xs) < window:
        return np.column_stack((xs, ys))
    left = window // 2
    right = window - 1 - left
    padded = np.pad(xs, (left, right), mode="edge")
    kernel = np.ones(window, dtype=np.float64) / float(window)
    xs = np.convolve(padded, kernel, mode="valid")
    return np.column_stack((xs, ys))


def extract_landmarks(contour, facing):
    contour = contour[np.argsort(contour[:, 1])]
    contour = _smooth(contour, 5)
    ys = contour[:, 1]
    top, bottom = ys.min(), ys.max()
    height = bottom - top
    if height <= 0:
        return None
    if facing == "right":
        front_val = lambda p: p[0]
    else:
        front_val = lambda p: -p[0]

    pronasale = _band(contour, top + 0.30 * height, top + 0.60 * height, front_val)
    glabella = _band(contour, top + 0.05 * height, top + 0.30 * height, front_val)
    if pronasale is None or glabella is None:
        return None

    nasion = _band(contour, glabella[1], pronasale[1], lambda p: -front_val(p))
    nose_length = distance(nasion, pronasale)
    if nose_length < 0.04 * height:
        return None
    subnasale = _band(contour, pronasale[1] + 0.02 * height, pronasale[1] + 0.16 * height, lambda p: -front_val(p))
    upper_lip = _band(contour, pronasale[1] + 0.08 * height, pronasale[1] + 0.24 * height, front_val)
    pogonion = _band(contour, top + 0.72 * height, top + 0.95 * height, front_val)
    if upper_lip is not None and pogonion is not None:
        lower_lip = _band(contour, upper_lip[1] + 0.02 * height, (upper_lip[1] + pogonion[1]) / 2.0, front_val)
        labiomental = _band(contour, (lower_lip[1] if lower_lip is not None else upper_lip[1]) + 0.02 * height, pogonion[1] - 0.02 * height, lambda p: -front_val(p))
    else:
        lower_lip = None
        labiomental = None
    cervical = _band(contour, top + 0.90 * height, bottom, lambda p: -front_val(p))
    neck_lower = contour[-1]

    return {
        "glabella": glabella,
        "nasion": nasion,
        "pronasale": pronasale,
        "subnasale": subnasale,
        "upper_lip": upper_lip,
        "lower_lip": lower_lip,
        "labiomental": labiomental,
        "pogonion": pogonion,
        "cervical": cervical,
        "neck_lower": np.asarray(neck_lower, dtype=np.float64),
    }


def compute_profile(landmarks, contour):
    glabella = landmarks["glabella"]
    nasion = landmarks["nasion"]
    pronasale = landmarks["pronasale"]
    subnasale = landmarks["subnasale"]
    upper_lip = landmarks["upper_lip"]
    lower_lip = landmarks["lower_lip"]
    labiomental = landmarks["labiomental"]
    pogonion = landmarks["pogonion"]
    cervical = landmarks["cervical"]
    neck_lower = landmarks["neck_lower"]

    nose_length = distance(nasion, pronasale)
    mm_per_px = NOSE_MM_NOMINAL / nose_length if nose_length else 1.0

    values = {}
    values["nasofrontal_angle"] = angle_degrees(glabella, nasion, pronasale)
    values["nasolabial_angle"] = angle_degrees(pronasale, subnasale, upper_lip) if upper_lip is not None else None
    values["facial_convexity"] = angle_degrees(glabella, subnasale, pogonion) if pogonion is not None else None
    values["total_convexity"] = angle_degrees(glabella, pronasale, pogonion) if pogonion is not None else None
    values["nasomental_angle"] = angle_degrees(nasion, pronasale, pogonion) if pogonion is not None else None
    values["nasofacial_angle"] = angle_degrees(pogonion, nasion, pronasale) if pogonion is not None else None
    values["mentolabial_angle"] = angle_degrees(lower_lip, labiomental, pogonion) if (lower_lip is not None and labiomental is not None and pogonion is not None) else None
    values["cervicomental_angle"] = angle_degrees(pogonion, cervical, neck_lower) if (pogonion is not None and cervical is not None) else None
    values["nasal_tip_angle"] = angle_degrees(nasion, pronasale, subnasale)

    facial_plane = _line(pogonion, nasion) if pogonion is not None else None
    projection = _point_line_distance(pronasale, facial_plane) if facial_plane is not None else None
    values["nasal_projection"] = projection / nose_length if (projection is not None and nose_length) else None

    eline = _line(pronasale, pogonion) if pogonion is not None else None
    if eline is not None:
        values["eline_upper"] = -_signed_point_line_distance(upper_lip, pronasale, pogonion) * mm_per_px if upper_lip is not None else None
        values["eline_lower"] = -_signed_point_line_distance(lower_lip, pronasale, pogonion) * mm_per_px if lower_lip is not None else None
    else:
        values["eline_upper"] = None
        values["eline_lower"] = None

    values["gonial_angle"] = _gonial_estimate(contour, pogonion)
    return values


def _line(a, b):
    return np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)


def _point_line_distance(point, line):
    a, b = line
    ab = b - a
    norm = np.linalg.norm(ab)
    if norm == 0:
        return 0.0
    return abs(_cross2d(ab, np.asarray(point, dtype=np.float64) - a)) / norm


def _signed_point_line_distance(point, a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    p = np.asarray(point, dtype=np.float64)
    ab = b - a
    norm = np.linalg.norm(ab)
    if norm == 0:
        return 0.0
    return float(_cross2d(ab, p - a) / norm)


def _cross2d(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _ratio(numerator, denominator):
    return float(numerator / denominator) if denominator else 0.0


def _line_angle(a, b):
    vector = np.asarray(b, dtype=np.float64) - np.asarray(a, dtype=np.float64)
    return float(np.degrees(np.arctan2(abs(vector[1]), abs(vector[0]))))


def _gonial_estimate(contour, chin):
    if chin is None:
        return None
    contour = contour[np.argsort(contour[:, 1])]
    ys = contour[:, 1]
    top, bottom = ys.min(), ys.max()
    lower_band = [p for p in contour if p[1] >= top + 0.70 * (bottom - top)]
    if not lower_band:
        return None
    gonion = lower_band[0]
    edge = np.asarray(gonion, dtype=np.float64) - np.asarray(chin, dtype=np.float64)
    return float(np.degrees(np.arctan2(abs(edge[1]), abs(edge[0]))))
