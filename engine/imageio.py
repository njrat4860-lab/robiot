import io

import numpy as np
from PIL import Image

MAX_DECODE_SIDE = 720


def decode(data):
    try:
        with Image.open(io.BytesIO(data)) as image:
            orientation = image.getexif().get(274, 1)
            image = image.convert("RGB")

            w, h = image.size
            if max(w, h) > MAX_DECODE_SIDE:
                scale = MAX_DECODE_SIDE / float(max(w, h))
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
                image = image.resize((new_w, new_h), Image.BILINEAR)
            array = np.asarray(image, dtype=np.uint8)
        return apply_orientation(array, orientation)
    except Exception:
        return None


def apply_orientation(array, orientation):
    if orientation == 1:
        return array
    if orientation == 2:
        return np.fliplr(array)
    if orientation == 3:
        return np.rot90(array, 2)
    if orientation == 4:
        return np.flipud(array)
    if orientation == 5:
        return np.transpose(array, (1, 0, 2))
    if orientation == 6:
        return np.rot90(array, 3)
    if orientation == 7:
        return np.fliplr(np.flipud(np.transpose(array, (1, 0, 2))))
    if orientation == 8:
        return np.rot90(array, 1)
    return array


def resize_longest_side(image, max_side, resample="lanczos"):
    height, width = image.shape[:2]
    if max(height, width) <= max_side:
        return image
    scale = max_side / float(max(height, width))
    new_w = max(1, int(width * scale))
    new_h = max(1, int(height * scale))

    if resample == "bilinear":
        pil_resample = Image.BILINEAR
    elif resample == "nearest":
        pil_resample = Image.NEAREST
    else:
        pil_resample = Image.LANCZOS if max_side > 480 else Image.BILINEAR
    with Image.fromarray(image) as pil:
        pil = pil.resize((new_w, new_h), pil_resample)
        return np.asarray(pil)


def to_gray(rgb):

    if rgb.ndim == 2:
        return rgb.astype(np.uint8)

    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    gray = (r * 0.299 + g * 0.587 + b * 0.114).astype(np.uint8)
    return gray


def to_ycrcb(rgb):
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cr = (r - y) * 0.713 + 128.0
    cb = (b - y) * 0.564 + 128.0
    return y, cr, cb


def skin_mask(rgb):

    h, w = rgb.shape[:2]
    if max(h, w) > 500:
        small = resize_longest_side(rgb, 500, resample="bilinear")
        y, cr, cb = to_ycrcb(small)

        sh, sw = small.shape[:2]
        cy0, cy1 = int(sh * 0.40), int(sh * 0.60)
        cx0, cx1 = int(sw * 0.35), int(sw * 0.65)
        cr_center = float(np.median(cr[cy0:cy1, cx0:cx1]))
        cb_center = float(np.median(cb[cy0:cy1, cx0:cx1]))
        mask_small = (
            (y > 25.0) & (y < 232.0)
            & (cr > cr_center - 9.0) & (cr < cr_center + 9.0)
            & (cb > cb_center - 11.0) & (cb < cb_center + 11.0)
        )

        with Image.fromarray(mask_small.astype(np.uint8) * 255) as pil:
            pil = pil.resize((w, h), Image.NEAREST)
            return np.asarray(pil) > 127
    else:
        y, cr, cb = to_ycrcb(rgb)
        height, width = rgb.shape[:2]
        cy0, cy1 = int(height * 0.40), int(height * 0.60)
        cx0, cx1 = int(width * 0.35), int(width * 0.65)
        cr_center = float(np.median(cr[cy0:cy1, cx0:cx1]))
        cb_center = float(np.median(cb[cy0:cy1, cx0:cx1]))
        return (
            (y > 25.0) & (y < 232.0)
            & (cr > cr_center - 9.0) & (cr < cr_center + 9.0)
            & (cb > cb_center - 11.0) & (cb < cb_center + 11.0)
        )


def laplacian(gray):

    g = gray.astype(np.float32)
    lap = np.zeros_like(g)
    lap[1:-1, 1:-1] = (
        g[2:, 1:-1] + g[:-2, 1:-1] + g[1:-1, 2:] + g[1:-1, :-2]
        - 4.0 * g[1:-1, 1:-1]
    )
    return lap
