from engine.geometry import face_center, rotate_points
from engine.pipeline import _looks_like_frontal
from tests.synthetic import ideal_face


def test_profile_mode_rejects_frontal_landmarks():
    assert _looks_like_frontal(ideal_face(), (400, 400)) is True


def test_profile_mode_does_not_reject_strong_roll_landmarks():
    landmarks = ideal_face()
    rolled = rotate_points(landmarks, face_center(landmarks), 24.0)

    assert _looks_like_frontal(rolled, (400, 400)) is False
