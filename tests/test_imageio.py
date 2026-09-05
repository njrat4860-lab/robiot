import io

import numpy as np
from PIL import Image, ImageOps

from engine.imageio import decode


def oriented_bytes(array, orientation):
    image = Image.fromarray(array)
    buffer = io.BytesIO()
    exif = Image.Exif()
    exif[274] = orientation
    image.save(buffer, format="PNG", exif=exif)
    return buffer.getvalue()


def ground_truth(data):
    image = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
    image.load()
    return np.asarray(image)


def test_decode_applies_exif_orientation():
    array = np.zeros((5, 7, 3), dtype=np.uint8)
    for row in range(5):
        for col in range(7):
            array[row, col] = (row * 30, col * 30, 100)
    for orientation in range(1, 9):
        data = oriented_bytes(array, orientation)
        assert np.array_equal(decode(data), ground_truth(data))


def test_decode_returns_none_on_garbage():
    assert decode(b"not an image") is None
