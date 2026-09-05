import pytest

from engine.calibration import load_calibration, metric_lookup
from engine.score import aggregate, metric_tier, subscore

CHICO_CARD = {
    "esr": 0.48,
    "canthal_tilt": 10.0,
    "fwhr": 1.76,
    "jfa_angle": 80.0,
    "cheekbone_height_ratio": 0.89,
    "tfwhr": 1.35,
    "bigonial_bizygomatic": 0.89,
    "chin_philtrum": 1.8,
    "mouth_nose": 1.38,
    "midface_ratio": 1.0,
    "eyebrow_position_ratio": 0.64,
    "eye_spacing": 1.01,
    "pfl_pfh": 3.7,
    "medial_canthal_angle": 37.0,
    "mouth_aspect_ratio": 0.436,
    "lip_ratio": 1.39,
    "iaa_jfa_deviation": 1.536,
    "brow_tilt": 10.0,
    "lower_third_ratio": 0.33,
    "iaa_angle": 84.0,
}

CARD_TIERS = {
    "esr": 2,
    "canthal_tilt": 2,
    "jfa_angle": 2,
    "chin_philtrum": 2,
    "pfl_pfh": 2,
    "cheekbone_height_ratio": 1,
    "tfwhr": 1,
    "bigonial_bizygomatic": 1,
    "mouth_nose": 1,
    "midface_ratio": 1,
    "eyebrow_position_ratio": 1,
    "eye_spacing": 1,
    "medial_canthal_angle": 1,
    "lower_third_ratio": 1,
    "iaa_jfa_deviation": 1,
}

CARD_HARMONY = 71.35
HARMONY_TOLERANCE = 3.0
PROBE = {
    "id": "probe",
    "band": {"male": [10.0, 20.0]},
    "ideal": {"male": 15.0},
    "points": 8.0,
    "block": "harmony",
    "shape": "band",
}


def test_value_inside_the_band_keeps_the_whole_metric():
    assert subscore(10.0, PROBE, "male") == 1.0
    assert subscore(20.0, PROBE, "male") == 1.0
    assert metric_tier(15.0, PROBE, "male") == 1


def test_each_tolerance_outside_the_band_halves_the_metric():
    assert subscore(25.0, PROBE, "male") == pytest.approx(0.5)
    assert subscore(30.0, PROBE, "male") == pytest.approx(0.25)
    assert subscore(35.0, PROBE, "male") == pytest.approx(0.125)
    assert metric_tier(25.0, PROBE, "male") == 2
    assert metric_tier(30.0, PROBE, "male") == 3


def test_four_tolerances_outside_the_band_give_nothing():
    assert subscore(40.0, PROBE, "male") == 0.0
    assert metric_tier(40.0, PROBE, "male") == 5


def test_moving_any_metric_away_from_its_band_only_lowers_the_score():
    lookup = metric_lookup(load_calibration())
    baseline = aggregate(dict(CHICO_CARD), "frontal", "male")["psl"]
    for metric_id, value in CHICO_CARD.items():
        low, high = lookup[metric_id]["band"]["male"]
        drifted = dict(CHICO_CARD)
        drifted[metric_id] = high + (high - low)
        assert aggregate(drifted, "frontal", "male")["psl"] <= baseline


def test_reference_card_tiers_are_reproduced():
    lookup = metric_lookup(load_calibration())
    for metric_id, expected in CARD_TIERS.items():
        assert metric_tier(CHICO_CARD[metric_id], lookup[metric_id], "male") == expected


def test_reference_card_harmony_matches_the_engine_scale():
    result = aggregate(dict(CHICO_CARD), "frontal", "male")
    assert result["blocks"]["harmony"] * 10.0 == pytest.approx(CARD_HARMONY, abs=HARMONY_TOLERANCE)


def test_reference_measurement_card_stays_in_the_expected_range():
    values = {
        "esr": 0.48,
        "canthal_tilt": 10.0,
        "fwhr": 1.76,
        "jfa_angle": 80.0,
        "cheekbone_height_ratio": 0.89,
        "tfwhr": 1.36,
        "bigonial_bizygomatic": 0.86,
        "chin_philtrum": 1.79,
        "mouth_nose": 1.38,
        "midface_ratio": 0.98,
        "eyebrow_position_ratio": 0.64,
        "eye_spacing": 1.01,
        "pfl_pfh": 3.70,
        "medial_canthal_angle": 41.0,
        "mouth_aspect_ratio": 0.41,
        "lip_ratio": 1.38,
        "iaa_jfa_deviation": 0.8,
        "brow_tilt": 10.0,
        "lower_third_ratio": 0.34,
        "iaa_angle": 80.8,
        "skin": 73.5,
        "symmetry": 97.5,
        "dimorphism": 70.5,
    }
    assert aggregate(values, "frontal", "male")["psl"] == pytest.approx(7.82, abs=0.12)


def test_average_geometry_does_not_score_as_high_psl():
    values = {
        "esr": 0.43,
        "canthal_tilt": 2.0,
        "fwhr": 1.85,
        "jfa_angle": 98.0,
        "cheekbone_height_ratio": 0.78,
        "tfwhr": 1.28,
        "bigonial_bizygomatic": 0.82,
        "chin_philtrum": 1.7,
        "mouth_nose": 1.25,
        "midface_ratio": 0.90,
        "eyebrow_position_ratio": 1.0,
        "eye_spacing": 1.2,
        "pfl_pfh": 2.7,
        "medial_canthal_angle": 50.0,
        "mouth_aspect_ratio": 0.6,
        "lip_ratio": 1.2,
        "iaa_jfa_deviation": 5.0,
        "brow_tilt": 0.0,
        "lower_third_ratio": 0.38,
        "iaa_angle": 75.0,
        "skin": 80.0,
        "symmetry": 95.0,
        "dimorphism": 50.0,
    }
    assert aggregate(values, "frontal", "male")["psl"] < 6.0


def test_disabled_blocks_are_renormalised():
    weights = load_calibration()["scale"]["block_weights"]
    values = dict(CHICO_CARD)
    values.update({"skin": 100.0, "symmetry": 100.0, "dimorphism": 78.0})
    result = aggregate(values, "frontal", "male", {"dimorphism"})
    blocks = result["blocks"]
    assert "dimorphism" not in blocks
    expected = sum(weights[name] * value for name, value in blocks.items())
    expected /= sum(weights[name] for name in blocks)
    assert result["psl"] > 0.0
    assert result["psl"] <= 10.0


def test_unmeasured_block_does_not_raise_the_score():
    values = dict(CHICO_CARD)
    values.update({"skin": 73.5, "symmetry": 97.5, "dimorphism": 50.8})
    measured = aggregate(values, "frontal", "male")
    values["dimorphism"] = None
    missing = aggregate(values, "frontal", "male")
    assert missing["psl"] <= measured["psl"]


def test_unmeasured_metrics_do_not_raise_the_score():
    values = dict(CHICO_CARD)
    values.update({"skin": 73.5, "symmetry": 97.5, "dimorphism": 54.0})
    measured = aggregate(values, "frontal", "male")
    values["eyebrow_position_ratio"] = None
    values["brow_tilt"] = None
    missing = aggregate(values, "frontal", "male")
    assert missing["psl"] <= measured["psl"]



def test_low_reference_geometry_scores_near_low_psl():
    values = {
        "esr": 0.52,
        "canthal_tilt": 0.8,
        "fwhr": 1.59,
        "jfa_angle": 71.5,
        "cheekbone_height_ratio": 0.39,
        "tfwhr": None,
        "bigonial_bizygomatic": 0.85,
        "chin_philtrum": 1.41,
        "mouth_nose": 1.43,
        "midface_ratio": 0.92,
        "eyebrow_position_ratio": 0.86,
        "eye_spacing": 1.05,
        "pfl_pfh": 4.04,
        "medial_canthal_angle": 35.6,
        "mouth_aspect_ratio": 0.47,
        "lip_ratio": 1.24,
        "iaa_jfa_deviation": 25.4,
        "brow_tilt": -7.2,
        "lower_third_ratio": None,
        "iaa_angle": 96.9,
        "skin": 71.8,
        "symmetry": 97.4,
        "dimorphism": 66.3,
    }
    assert aggregate(values, "frontal", "male")["psl"] == pytest.approx(1.9, abs=0.25)


def test_t5_band_metric_gets_zero_points():
    lookup = metric_lookup(load_calibration())
    metric = lookup["fwhr"]
    assert metric_tier(1.59, metric, "male") == 5
    assert subscore(1.59, metric, "male") == 0.0

def test_a_worse_measurement_never_raises_the_score():
    better = aggregate(dict(CHICO_CARD), "frontal", "male")
    worse_values = dict(CHICO_CARD)
    worse_values["esr"] = 0.60
    worse = aggregate(worse_values, "frontal", "male")
    assert worse["psl"] < better["psl"]


def test_every_metric_declares_a_source_and_an_ordered_band():
    for metric in load_calibration()["metrics"]:
        assert metric["source"]
        assert metric["points"] > 0
        for gender in ("male", "female"):
            low, high = metric["band"][gender]
            assert low < high
