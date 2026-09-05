from engine.metrics.frontal import compute_frontal
from tests.synthetic import ideal_face


WIDTH_METRICS = (
    "esr",
    "fwhr",
    "tfwhr",
    "bigonial_bizygomatic",
)


def test_width_metrics_are_missing_when_eye_widths_show_perspective_turn():
    landmarks = ideal_face()
    landmarks[42, 0] += 10.0
    landmarks[45, 0] -= 10.0

    values = compute_frontal(landmarks, None)

    for metric_id in WIDTH_METRICS:
        assert values[metric_id] is None


def test_width_metrics_stay_available_on_symmetric_frontal_landmarks():
    values = compute_frontal(ideal_face(), None)

    assert values["esr"] is not None
    assert values["fwhr"] is not None
    assert values["bigonial_bizygomatic"] is not None
