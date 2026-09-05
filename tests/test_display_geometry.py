import numpy as np

from engine import pipeline
from engine.geometry import face_center, rotate_points
from tests.synthetic import ideal_face


class Engine:
    def __init__(self, landmarks):
        self.landmarks = landmarks

    def detect_frontal(self, image_rgb):
        return self.landmarks, (20, 20, 220, 220)


async def noop():
    return None


def test_frontal_result_keeps_original_landmarks_for_display(monkeypatch):
    image = np.full((260, 260, 3), 180, dtype=np.uint8)
    landmarks = rotate_points(ideal_face(), face_center(ideal_face()), 12.0)
    hairline = np.array([100.0, 30.0], dtype=np.float64)

    monkeypatch.setattr(pipeline, "_engine", lambda: Engine(landmarks))
    monkeypatch.setattr(pipeline, "estimate_hairline", lambda image_rgb, points, top: (hairline, None))
    monkeypatch.setattr(pipeline, "compute_skin_score", lambda image_rgb, points: 80.0)

    result = pipeline._analyze_frontal(image, "male", pipeline.load_calibration(), frozenset())

    assert np.allclose(result["landmarks"], landmarks)
    assert np.allclose(result["hairline"], hairline)
    assert result["image"].shape == image.shape
