import numpy as np

from engine.hairline import estimate

IMAGE_SIZE = 400
FACE_LEFT = 120
FACE_RIGHT = 280
BROW_Y = 200
HAIRLINE_Y = 170
BOX_TOP = 110
SKIN_COLOR = (222, 178, 150)
DARK_HAIR_COLOR = (40, 30, 28)
SIMILAR_HAIR_COLOR = (216, 174, 148)


def test_hairline_is_measured_when_hair_contrasts_with_skin():
    image = _face_image(DARK_HAIR_COLOR)
    point, warning = estimate(image, _landmarks(), BOX_TOP)
    assert warning is None
    assert abs(point[1] - HAIRLINE_Y) <= 12


def test_hairline_is_missing_when_boundary_is_not_detected():
    image = np.full((IMAGE_SIZE, IMAGE_SIZE, 3), SKIN_COLOR, dtype=np.uint8)
    point, warning = estimate(image, _landmarks(), BOX_TOP)
    assert point is None
    assert warning is not None


def test_ear_level_hair_does_not_move_the_hairline():
    image = _face_image(DARK_HAIR_COLOR)
    image[:, :FACE_LEFT + 20] = DARK_HAIR_COLOR
    image[:, FACE_RIGHT - 20:] = DARK_HAIR_COLOR
    point, warning = estimate(image, _landmarks(), BOX_TOP)
    assert warning is None
    assert abs(point[1] - HAIRLINE_Y) <= 12


def _face_image(hair_color):
    image = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    image[:, :] = hair_color
    image[HAIRLINE_Y:, FACE_LEFT:FACE_RIGHT] = SKIN_COLOR
    return image


def _landmarks():
    points = np.zeros((68, 2), dtype=np.float64)
    points[0] = [FACE_LEFT, BROW_Y + 40]
    points[16] = [FACE_RIGHT, BROW_Y + 40]
    points[17:27] = [200.0, BROW_Y]
    points[27] = [200.0, BROW_Y + 20]
    points[33] = [200.0, BROW_Y + 70]
    points[8] = [200.0, BROW_Y + 120]
    return points


TALL_FOREHEAD_HAIRLINE_Y = 160
FOREHEAD_SHADING_STEP = 3.0


def test_shaded_tall_forehead_keeps_the_hairline_at_the_hair_boundary():
    image = _tall_forehead_image(DARK_HAIR_COLOR)
    point, warning = estimate(image, _tall_forehead_landmarks(), BOX_TOP)
    assert warning is None
    assert abs(point[1] - TALL_FOREHEAD_HAIRLINE_Y) <= 12


def _tall_forehead_image(hair_color):
    image = np.zeros((IMAGE_SIZE, IMAGE_SIZE, 3), dtype=np.uint8)
    image[:, :] = hair_color
    for row in range(TALL_FOREHEAD_HAIRLINE_Y, IMAGE_SIZE):
        shade = (row - TALL_FOREHEAD_HAIRLINE_Y) * FOREHEAD_SHADING_STEP
        color = tuple(int(min(255.0, channel + shade)) for channel in SKIN_COLOR)
        image[row, FACE_LEFT:FACE_RIGHT] = color
    return image


def _tall_forehead_landmarks():
    points = np.zeros((68, 2), dtype=np.float64)
    points[0] = [FACE_LEFT, 260.0]
    points[16] = [FACE_RIGHT, 260.0]
    points[17:27] = [200.0, 210.0]
    points[27] = [200.0, 220.0]
    points[33] = [200.0, 270.0]
    points[8] = [200.0, 330.0]
    return points
