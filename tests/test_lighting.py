import numpy as np

from engine.lighting import analyze, assess

LIMITS = {
    "min_brightness": 40.0,
    "max_brightness": 225.0,
    "min_contrast": 25.0,
    "clipped_ratio": 0.08,
}


def test_single_dark_background_does_not_trigger_clipping_warning():
    image = np.full((100, 100), 120, dtype=np.uint8)
    image[:, :7] = 0

    warnings = assess(analyze(image), LIMITS)

    assert "сильные засветы или провалы в тенях" not in warnings


def test_real_dark_and_light_clipping_triggers_warning():
    image = np.full((100, 100), 120, dtype=np.uint8)
    image[:, :5] = 0
    image[:, -5:] = 255

    warnings = assess(analyze(image), LIMITS)

    assert "сильные засветы или провалы в тенях" in warnings
