import numpy as np

from engine.metrics.profile import extract_landmarks, compute_profile


def _profile_contour():
    profile = [
        (150, 0), (155, 30), (160, 60), (164, 90), (166, 110),
        (162, 130), (156, 150), (150, 170), (152, 190), (160, 210),
        (172, 230), (188, 250), (200, 270), (196, 290), (172, 305),
        (158, 318), (168, 335), (178, 348), (188, 356), (182, 368),
        (164, 378), (150, 390), (168, 408), (182, 424), (178, 440),
        (162, 452), (150, 465), (152, 480), (158, 500), (160, 530),
        (158, 560), (156, 590),
    ]
    return np.array(profile, dtype=np.float64)


def test_profile_landmarks_extract():
    contour = _profile_contour()
    landmarks = extract_landmarks(contour, "right")
    assert landmarks is not None
    for key in ("glabella", "nasion", "pronasale", "subnasale", "pogonion"):
        assert landmarks[key] is not None


def test_profile_compute_finite():
    contour = _profile_contour()
    landmarks = extract_landmarks(contour, "right")
    values = compute_profile(landmarks, contour)
    for key, value in values.items():
        if value is not None:
            assert np.isfinite(value)
    assert 150 < values["facial_convexity"] < 180


def test_profile_angles_reasonable():
    contour = _profile_contour()
    landmarks = extract_landmarks(contour, "right")
    values = compute_profile(landmarks, contour)
    assert 80 < values["nasofrontal_angle"] < 175
    assert 40 < values["nasolabial_angle"] < 175
    assert 0.2 < values["nasal_projection"] < 1.0
