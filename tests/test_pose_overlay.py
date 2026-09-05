import numpy as np

from engine.pose import estimate_pose, normalize_landmarks, normalize_points
from tests.synthetic import ideal_face


def test_hairline_uses_same_pose_normalization_as_landmarks():
    landmarks = ideal_face()
    hairline = np.array([100.0, 32.0], dtype=np.float64)
    yaw, pitch, roll = estimate_pose(landmarks, (400, 400))

    normalized_landmarks = normalize_landmarks(landmarks, yaw, pitch, roll)
    normalized_hairline = normalize_points([hairline], landmarks, yaw, pitch, roll)[0]

    assert normalized_landmarks.shape == landmarks.shape
    assert normalized_hairline.shape == hairline.shape
