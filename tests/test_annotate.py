import io

import numpy as np
from PIL import Image

from engine.annotate import build_summary_image


def test_summary_image_has_no_text_caption():
    image = np.full((240, 320, 3), 180, dtype=np.uint8)
    result = {
        "metrics": {},
        "landmarks": None,
        "profile_points": None,
        "contour": None,
        "hairline": None,
    }

    data = build_summary_image(image, result, [])
    frame = Image.open(io.BytesIO(data))

    assert data.startswith(b"\xff\xd8")
    assert frame.size == (320, 240)


def test_summary_image_crops_to_face():
    image = np.full((400, 400, 3), 180, dtype=np.uint8)
    landmarks = np.array([[180.0, 160.0]] * 68)
    landmarks[0] = [150.0, 210.0]
    landmarks[16] = [250.0, 210.0]
    landmarks[8] = [200.0, 270.0]
    landmarks[27] = [200.0, 160.0]
    result = {
        "metrics": {"facial_index": {"name_ru": "Индекс лица"}},
        "landmarks": landmarks,
        "profile_points": None,
        "contour": None,
        "hairline": None,
    }

    data = build_summary_image(image, result, ["facial_index"])
    frame = Image.open(io.BytesIO(data))

    assert frame.size[0] < 400
    assert frame.size[1] < 400
