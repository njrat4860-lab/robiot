import os
import numpy as np

from engine import imageio

MMOD_MAX_SIDE = 256
CONTRAST_LOW_PERCENTILE = 2.0
CONTRAST_HIGH_PERCENTILE = 98.0
DETECT_MAX_SIDE = 512
MIN_PROFILE_ROWS = 12
PROFILE_OUTLIER_SPREADS = 4.0
ENABLE_MMOD = os.getenv("ENABLE_MMOD", "0") == "1"


class LandmarkEngine:
    def __init__(self, predictor_path, mmod_path=None):
        self.dlib = _load_dlib()
        self.detector = self.dlib.get_frontal_face_detector()
        self.predictor = self.dlib.shape_predictor(predictor_path)
        self.mmod = None
        if ENABLE_MMOD and mmod_path is not None:
            try:
                self.mmod = self.dlib.cnn_face_detection_model_v1(mmod_path)
            except RuntimeError:
                self.mmod = None

    def detect_frontal(self, image_rgb):
        rect = self._detect_rect(image_rgb)
        if rect is None:
            return None, None
        gray = imageio.to_gray(image_rgb)
        landmarks = self._predict(gray, rect)
        box = (rect.left(), rect.top(), rect.right(), rect.bottom())
        return landmarks, box

    def _detect_rect(self, image_rgb):
        height, width = image_rgb.shape[:2]
        scale = 1.0
        small = image_rgb
        if max(height, width) > DETECT_MAX_SIDE:
            small = imageio.resize_longest_side(image_rgb, DETECT_MAX_SIDE, resample="bilinear")
            scale = max(height, width) / float(max(small.shape[:2]))
        gray = imageio.to_gray(small)
        rects = self._detect_rects(gray)
        if not rects:
            return None
        rect = max(rects, key=lambda item: item.width() * item.height())
        if scale == 1.0:
            return rect
        return self.dlib.rectangle(
            int(rect.left() * scale),
            int(rect.top() * scale),
            int(rect.right() * scale),
            int(rect.bottom() * scale),
        )

    def _predict(self, gray, rect):
        shape = self.predictor(gray, rect)
        return np.array([[shape.part(i).x, shape.part(i).y] for i in range(68)], dtype=np.float64)

    def detect_face_box(self, image_rgb):
        rect = self._detect_rect(image_rgb)
        if rect is None:
            return None
        return rect.left(), rect.top(), rect.right(), rect.bottom()

    def _detect_rects(self, gray):
        rects = self._hog_rects(gray, upsample=1)
        if rects:
            return rects
        enhanced = _contrast_stretch(gray)
        if not np.array_equal(enhanced, gray):
            rects = self._hog_rects(enhanced, upsample=1)
            if rects:
                return rects
        if max(gray.shape) <= 700:
            rects = self._hog_rects(gray, upsample=2)
            if rects:
                return rects
            if not np.array_equal(enhanced, gray):
                rects = self._hog_rects(enhanced, upsample=2)
                if rects:
                    return rects
        if self.mmod is None:
            return []
        rects = self._mmod_rects(gray)
        if rects:
            return rects
        if not np.array_equal(enhanced, gray):
            rects = self._mmod_rects(enhanced)
            if rects:
                return rects
        return []

    def _hog_rects(self, gray, upsample=1):
        try:
            rects = self.detector(gray, upsample)
            if rects:
                return list(rects)
        except Exception:
            return []
        return []

    def _mmod_rects(self, gray):
        downscaled = imageio.resize_longest_side(gray, MMOD_MAX_SIDE, resample="bilinear")
        scale_y = gray.shape[0] / float(downscaled.shape[0]) if downscaled.shape[0] else 1.0
        scale_x = gray.shape[1] / float(downscaled.shape[1]) if downscaled.shape[1] else 1.0
        try:
            detections = self.mmod(downscaled, 1)
        except (RuntimeError, MemoryError):
            return []
        rects = []
        for detection in detections:
            rect = detection.rect
            rects.append(self.dlib.rectangle(
                int(rect.left() * scale_x),
                int(rect.top() * scale_y),
                int(rect.right() * scale_x),
                int(rect.bottom() * scale_y),
            ))
        return rects


def extract_profile_silhouette(image_rgb, box, facing):
    height, width = image_rgb.shape[:2]
    left, top, right, bottom = box
    margin_x = int((right - left) * 0.35)
    margin_y = int((bottom - top) * 0.5)
    x0 = max(0, left - margin_x)
    x1 = min(width, right + margin_x)
    y0 = max(0, top - margin_y)
    y1 = min(height, bottom + margin_y)
    crop = image_rgb[y0:y1, x0:x1]
    if max(crop.shape[:2]) > 400:
        crop_small = imageio.resize_longest_side(crop, 400, resample="bilinear")
    else:
        crop_small = crop
    mask = imageio.skin_mask(crop_small)
    if crop_small.shape[:2] != crop.shape[:2]:
        try:
            from PIL import Image
            pil = Image.fromarray(mask.astype(np.uint8) * 255)
            pil = pil.resize((crop.shape[1], crop.shape[0]), Image.NEAREST)
            mask = np.asarray(pil) > 127
        except Exception:
            return None
    curve = _profile_curve(mask, facing)
    if curve is None or len(curve) < 12:
        return None
    curve = curve.astype(np.float64)
    if crop_small.shape[:2] != crop.shape[:2]:
        sy = crop.shape[0] / float(crop_small.shape[0])
        sx = crop.shape[1] / float(crop_small.shape[1])
        curve[:, 0] *= sx
        curve[:, 1] *= sy
    curve[:, 0] += x0
    curve[:, 1] += y0
    return curve


def _load_dlib():
    try:
        import dlib
    except ModuleNotFoundError as error:
        raise RuntimeError("dlib не установлен: установи зависимости из requirements.txt") from error
    return dlib


def _contrast_stretch(gray):
    low, high = np.percentile(gray, [CONTRAST_LOW_PERCENTILE, CONTRAST_HIGH_PERCENTILE])
    if high - low < 8.0:
        return gray
    stretched = (gray.astype(np.float32) - low) * 255.0 / (high - low)
    return np.clip(stretched, 0.0, 255.0).astype(np.uint8)


def _profile_curve(mask, facing):
    rows = np.where(mask.any(axis=1))[0]
    if rows.size == 0:
        return None
    last_column = mask.shape[1] - 1
    xs = []
    ys = []
    for row in rows:
        cols = np.where(mask[row])[0]
        if cols.size == 0:
            continue
        column = cols[0] if facing == "left" else cols[-1]
        if column == 0 or column == last_column:
            continue
        xs.append(column)
        ys.append(row)
    if len(xs) < MIN_PROFILE_ROWS:
        return None
    curve = np.array([[x, y] for x, y in zip(xs, ys)], dtype=np.float64)
    return _drop_outlier_rows(curve, facing)


def _drop_outlier_rows(curve, facing):
    columns = curve[:, 0]
    center = float(np.median(columns))
    spread = float(np.median(np.abs(columns - center)))
    if spread <= 0.0:
        return curve
    limit = PROFILE_OUTLIER_SPREADS * spread
    keep = np.abs(columns - center) <= limit
    if int(keep.sum()) < MIN_PROFILE_ROWS:
        return curve
    return curve[keep]
