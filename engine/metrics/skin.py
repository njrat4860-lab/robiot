import numpy as np

from engine import imageio
from engine.geometry import eye_centers

MIN_PIXELS = 40
MIN_SKIN_RATIO = 0.35
TONE_WEIGHT = 0.25
TEXTURE_WEIGHT = 0.45
REDNESS_WEIGHT = 0.15
DARK_CIRCLES_WEIGHT = 0.15
SKIN_CR_CENTER = 145.0
SKIN_CB_CENTER = 110.0
CHROMA_SOFTNESS = 28.0
TONE_PENALTY = 1.45
TEXTURE_PENALTY = 2.30
REDNESS_PENALTY = 0.70
DARK_CIRCLE_PENALTY = 5.0
SEVERE_TEXTURE_THRESHOLD = 40.0
SEVERE_TEXTURE_PENALTY = 1.6
SKIN_MAX_SIDE = 384


def compute_skin_score(image_rgb, landmarks):

    h, w = image_rgb.shape[:2]
    scale = 1.0
    if max(h, w) > SKIN_MAX_SIDE:
        small = imageio.resize_longest_side(image_rgb, SKIN_MAX_SIDE, resample="bilinear")
        scale = max(h, w) / float(SKIN_MAX_SIDE)

        landmarks_small = landmarks / scale
    else:
        small = image_rgb
        landmarks_small = landmarks

    gray = imageio.to_gray(small)
    y_channel, cr_channel, cb_channel = imageio.to_ycrcb(small)
    lap = imageio.laplacian(gray)
    skin_mask = _adaptive_skin_mask(small)
    patches = _skin_patches(landmarks_small, small.shape[:2])

    tone = []
    redness = []
    texture = []
    for x0, x1, y0, y1 in patches:
        mask = skin_mask[y0:y1, x0:x1]
        if mask.size == 0 or float(mask.mean()) < MIN_SKIN_RATIO:
            continue
        region_y = y_channel[y0:y1, x0:x1][mask]
        region_cr = cr_channel[y0:y1, x0:x1][mask]
        region_lap = np.abs(lap[y0:y1, x0:x1][mask])
        if region_y.size < MIN_PIXELS:
            continue
        tone.append(_tone_irregularity(region_y))
        redness.append(_redness_excess(region_cr))
        texture.append(_texture_strength(region_lap))

    if not tone:
        return None

    tone_score = _clamp(100.0 - float(np.mean(tone)) * TONE_PENALTY, 0.0, 100.0)
    texture_score = _clamp(100.0 - float(np.mean(texture)) * TEXTURE_PENALTY, 0.0, 100.0)
    redness_score = _clamp(100.0 - float(np.mean(redness)) * REDNESS_PENALTY, 0.0, 100.0)
    dark_score = _clamp(100.0 - _dark_circle_severity(y_channel, skin_mask, landmarks_small) * DARK_CIRCLE_PENALTY, 0.0, 100.0)

    texture_mean = float(np.mean(texture))
    combined = (
        TONE_WEIGHT * tone_score
        + TEXTURE_WEIGHT * texture_score
        + REDNESS_WEIGHT * redness_score
        + DARK_CIRCLES_WEIGHT * dark_score
    )
    severe_texture = max(0.0, texture_mean - SEVERE_TEXTURE_THRESHOLD) * SEVERE_TEXTURE_PENALTY
    return float(_clamp(combined - severe_texture, 0.0, 100.0))


def _adaptive_skin_mask(rgb):
    y, cr, cb = imageio.to_ycrcb(rgb)
    base = (
        (y > 45.0) & (y < 245.0)
        & (cr > 120.0) & (cr < 175.0)
        & (cb > 80.0) & (cb < 140.0)
    )
    chroma_distance = np.sqrt((cr - SKIN_CR_CENTER) ** 2 + (cb - SKIN_CB_CENTER) ** 2)
    soft = chroma_distance < CHROMA_SOFTNESS
    return base | ((y > 50.0) & (y < 235.0) & soft)


def _skin_patches(landmarks, shape):
    height, width = shape
    nasion = landmarks[27]
    chin = landmarks[8]
    right_eye, left_eye = eye_centers(landmarks)
    ipd = float(np.linalg.norm(right_eye - left_eye))
    if ipd == 0:
        return []
    eye_y = float((right_eye[1] + left_eye[1]) / 2.0)
    brow_y = float(landmarks[17:27, 1].min())
    mouth_y = float(landmarks[62:68, 1].max())
    cheek_y = eye_y + ipd * 0.62
    cheek_half = ipd * 0.20
    cheek_size = ipd * 0.42
    forehead_half = ipd * 0.16
    forehead_size = ipd * 0.55
    chin_half = ipd * 0.15
    chin_size = ipd * 0.42

    patches = []
    patches.append(_rect(nasion[0], brow_y - ipd * 0.30, forehead_half, forehead_size, height, width))
    patches.append(_rect(right_eye[0] - ipd * 0.34, cheek_y, cheek_half, cheek_size, height, width))
    patches.append(_rect(left_eye[0] + ipd * 0.34, cheek_y, cheek_half, cheek_size, height, width))
    patches.append(_rect(chin[0], mouth_y + ipd * 0.34, chin_half, chin_size, height, width))
    return [patch for patch in patches if patch is not None]


def _rect(center_x, center_y, half, size, height, width):
    half_w = max(4.0, size / 2.0)
    x0 = int(max(0, center_x - half_w))
    x1 = int(min(width, center_x + half_w))
    y0 = int(max(0, center_y - half))
    y1 = int(min(height, center_y + half))
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, x1, y0, y1


def _tone_irregularity(values):
    values = np.asarray(values, dtype=np.float64)
    low, high = np.percentile(values, [10.0, 90.0])
    dynamic = max(high - low, 35.0)
    clipped = values[(values >= low) & (values <= high)]
    if clipped.size == 0:
        clipped = values
    return float(np.std((clipped - np.median(clipped)) / dynamic * 100.0))


def _texture_strength(values):
    values = np.asarray(values, dtype=np.float64)
    return float(np.percentile(values, 70.0))


def _redness_excess(values):
    values = np.asarray(values, dtype=np.float64)
    return float(max(0.0, np.percentile(values, 65.0) - 150.0))


def _dark_circle_severity(y_channel, skin_mask, landmarks):
    right_center, left_center = eye_centers(landmarks)
    eye_width = np.linalg.norm(landmarks[36] - landmarks[39])
    if eye_width == 0:
        return 0.0
    pad = int(eye_width * 0.45)
    band = int(eye_width * 0.42)
    severity = []
    for center in (right_center, left_center):
        cx, cy = int(center[0]), int(center[1]) + int(eye_width * 0.75)
        x0 = max(0, cx - pad)
        x1 = min(y_channel.shape[1], cx + pad)
        under_y0 = max(0, cy - band)
        under_y1 = min(y_channel.shape[0], cy)
        cheek_y0 = min(y_channel.shape[0], cy)
        cheek_y1 = min(y_channel.shape[0], cy + band)
        under_mask = skin_mask[under_y0:under_y1, x0:x1]
        cheek_mask = skin_mask[cheek_y0:cheek_y1, x0:x1]
        under = y_channel[under_y0:under_y1, x0:x1][under_mask]
        cheek = y_channel[cheek_y0:cheek_y1, x0:x1][cheek_mask]
        if under.size < MIN_PIXELS or cheek.size < MIN_PIXELS:
            continue
        severity.append(max(0.0, float(np.median(cheek) - np.median(under))))
    return float(np.mean(severity)) if severity else 0.0


def _clamp(value, low, high):
    return float(max(low, min(high, value)))
