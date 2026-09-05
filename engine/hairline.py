import numpy as np

from engine import imageio
from engine.constants import NASION, SUBNASALE
from engine.geometry import distance

MIN_FOREHEAD_RATIO = 0.28
MIN_STABLE_FOREHEAD_RATIO = 0.65
MAX_STABLE_FOREHEAD_RATIO = 1.45
CENTRAL_STRIP_RATIO = 0.22
MIN_SKIN_ROW_RATIO = 0.34
MAX_HAIR_ROW_RATIO = 0.20
MIN_COLOR_TRANSITION = 25.0
CONSECUTIVE_ROWS = 4
MIN_HALF_WIDTH = 6
HAIRLINE_NOT_FOUND = "линия роста волос не найдена - tFWHR и нижняя треть не начислены"


def estimate(image_rgb, landmarks, box_top):
    width = image_rgb.shape[1]
    skin = imageio.skin_mask(image_rgb)
    nasion = landmarks[NASION]
    mid_height = distance(nasion, landmarks[SUBNASALE])

    brow_y = int(min(landmarks[17:27, 1].min(), nasion[1]))
    strip_top = max(0, int(box_top))
    half_width = max(MIN_HALF_WIDTH, int(distance(landmarks[0], landmarks[16]) * CENTRAL_STRIP_RATIO))
    x0 = int(max(0, nasion[0] - half_width))
    x1 = int(min(width - 1, nasion[0] + half_width))

    row = _transition_row(image_rgb[strip_top:brow_y, x0:x1 + 1])
    if row is None:
        row = _hairline_row(skin[strip_top:brow_y, x0:x1 + 1])
    if row is None:
        return None, HAIRLINE_NOT_FOUND

    hairline_y = strip_top + row
    forehead_height = float(nasion[1] - hairline_y)
    if brow_y - hairline_y < MIN_FOREHEAD_RATIO * mid_height:
        return None, HAIRLINE_NOT_FOUND
    if forehead_height < MIN_STABLE_FOREHEAD_RATIO * mid_height:
        return None, HAIRLINE_NOT_FOUND
    if forehead_height > MAX_STABLE_FOREHEAD_RATIO * mid_height:
        return None, HAIRLINE_NOT_FOUND
    return np.array([nasion[0], float(hairline_y)]), None


def _transition_row(strip):
    if strip.size == 0 or strip.shape[0] < CONSECUTIVE_ROWS * 2:
        return None
    rows = strip.astype(np.float32).mean(axis=1)
    changes = np.linalg.norm(np.diff(rows, axis=0), axis=1)
    if changes.size == 0:
        return None
    row = int(np.argmax(changes)) + 1
    if float(changes[row - 1]) < MIN_COLOR_TRANSITION:
        return None
    return row


def _hairline_row(strip):
    if strip.size == 0:
        return None
    skin_ratio = strip.mean(axis=1)
    if skin_ratio.size < CONSECUTIVE_ROWS * 2:
        return None
    skin_runs = np.convolve((skin_ratio >= MIN_SKIN_ROW_RATIO).astype(np.int32), np.ones(CONSECUTIVE_ROWS, dtype=np.int32), mode="valid")
    hair_runs = np.convolve((skin_ratio <= MAX_HAIR_ROW_RATIO).astype(np.int32), np.ones(CONSECUTIVE_ROWS, dtype=np.int32), mode="valid")
    skin_rows = np.where(skin_runs >= CONSECUTIVE_ROWS)[0]
    for row in skin_rows:
        before = hair_runs[:row]
        if before.size and before.max() >= CONSECUTIVE_ROWS:
            return int(row)
    return None
