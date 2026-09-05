import numpy as np
import pytest

from engine.calibration import load_calibration, metric_lookup
from engine.metrics.frontal import compute_frontal
from engine.score import subscore
from tests.synthetic import ideal_face


SKIN_COLOR = (210, 165, 140)
HAIR_COLOR = (35, 25, 20)


def test_brow_metrics_are_missing_when_fringe_covers_the_brow_zone():
    landmarks = ideal_face()
    image = np.full((240, 240, 3), SKIN_COLOR, dtype=np.uint8)
    image[:82, 55:145] = HAIR_COLOR

    values = compute_frontal(landmarks, None, image_rgb=image)

    assert values["brow_tilt"] is None
    assert values["eyebrow_position_ratio"] is None
    assert values["fwhr"] is None


def test_visible_brows_with_high_dlib_gap_are_calibrated_not_dropped():
    landmarks = ideal_face()
    image = np.full((240, 240, 3), SKIN_COLOR, dtype=np.uint8)

    values = compute_frontal(landmarks, None, image_rgb=image)

    assert values["eyebrow_position_ratio"] == pytest.approx(0.62, abs=0.04)
    assert values["brow_tilt"] is not None
    assert values["fwhr"] is not None
    assert values["dimorphism"] is not None


def test_brow_tilt_ignores_unreliable_landmark_points():
    landmarks = ideal_face()
    landmarks[17:27, 1] = -80.0

    values = compute_frontal(landmarks, None)

    assert values["brow_tilt"] is None


def test_brow_tilt_inside_the_band_keeps_all_points():
    metric = metric_lookup(load_calibration())["brow_tilt"]

    assert subscore(8.0, metric, "male") == 1.0
    assert subscore(-1.8, metric, "male") < subscore(5.0, metric, "male")
