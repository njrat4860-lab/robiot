import numpy as np

from engine.metrics.skin import compute_skin_score
from tests.synthetic import ideal_face


def test_clean_skin_stays_high_with_hair_colored_regions():
    image = np.full((260, 220, 3), (184, 132, 104), dtype=np.uint8)
    image[:75, 35:185] = (42, 30, 24)
    image[92:112, 54:146] = (36, 26, 20)
    landmarks = ideal_face()

    score = compute_skin_score(image, landmarks)

    assert score is not None
    assert score >= 78.0


def test_strong_skin_texture_lowers_score():
    rng = np.random.default_rng(7)
    image = np.full((260, 220, 3), (184, 132, 104), dtype=np.uint8)
    noise = rng.normal(0.0, 42.0, image.shape).astype(np.int16)
    damaged = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    landmarks = ideal_face()

    clean_score = compute_skin_score(image, landmarks)
    damaged_score = compute_skin_score(damaged, landmarks)

    assert clean_score is not None
    assert damaged_score is not None
    assert damaged_score < clean_score


def test_severe_skin_damage_scores_low():
    image = np.full((260, 220, 3), (174, 122, 98), dtype=np.uint8)
    for row in range(70, 220, 12):
        image[row:row + 3, 45:175] = (84, 52, 44)
    for col in range(55, 175, 18):
        image[80:230, col:col + 2] = (215, 160, 130)
    rng = np.random.default_rng(11)
    noise = rng.normal(0.0, 35.0, image.shape).astype(np.int16)
    image = np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    landmarks = ideal_face()

    score = compute_skin_score(image, landmarks)

    assert score is not None
    assert score <= 35.0
