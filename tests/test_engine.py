import numpy as np
import pytest

from engine.calibration import load_calibration, load_advice, metrics_by_group
from engine.constants import CHIN, JAW_GONION_LEFT, JAW_GONION_RIGHT, LIP_LOWER, LIP_UPPER, SUBNASALE
from engine.geometry import angle_degrees, distance, eye_centers, midpoint
from engine.metrics.frontal import compute_frontal, face_width
from engine.score import aggregate, subscore
from engine.pose import normalize_landmarks, estimate_pose
from tests.synthetic import ideal_face, tilted_face

CALIBRATION = load_calibration()


def test_calibration_structure():
    for metric in CALIBRATION["metrics"]:
        for key in ("id", "name_ru", "group", "block", "shape", "points", "ideal", "band", "source"):
            assert key in metric
        for gender in ("male", "female"):
            assert gender in metric["ideal"]
            assert gender in metric["band"]
            lo, hi = metric["band"][gender]
            assert lo <= hi
        assert metric["points"] > 0


def test_metric_ids_are_unique():
    ids = [metric["id"] for metric in CALIBRATION["metrics"]]
    assert len(ids) == len(set(ids))


def test_advice_coverage():
    advice = load_advice()
    for metric in CALIBRATION["metrics"]:
        bucket = advice.get(metric["id"])
        assert bucket is not None
        for direction in ("high", "low"):
            assert len(bucket.get(direction, [])) >= 2


def test_symmetry_ideal():
    values = compute_frontal(ideal_face(), None)
    assert values["symmetry"] > 95.0


def test_canthal_tilt_of_level_eyes_equals_the_landmark_correction():
    correction = _correction("canthal_tilt")["offset"]
    values = compute_frontal(ideal_face(), None)
    assert values["canthal_tilt"] == pytest.approx(correction, abs=0.5)


def _correction(metric_id):
    return next(m for m in CALIBRATION["metrics"] if m["id"] == metric_id)["landmark_correction"]


def test_fwhr_is_face_width_over_brow_to_upper_lip():
    landmarks = ideal_face()
    width = face_width(landmarks)

    assert width == pytest.approx(180.0, abs=20.0)
    values = compute_frontal(landmarks, None)
    brow = midpoint(np.mean(landmarks[17:22], axis=0), np.mean(landmarks[22:27], axis=0))

    raw = width / distance(brow, landmarks[51])
    assert values["fwhr"] == pytest.approx(raw * _correction("fwhr")["scale"], rel=1e-6)


def test_subscore_band():
    metric = CALIBRATION["metrics"][0]
    band_lo, band_hi = metric["band"]["male"]
    step = (band_hi - band_lo) / 2.0
    assert subscore(band_lo, metric, "male") == pytest.approx(1.0)
    assert subscore(band_hi, metric, "male") == pytest.approx(1.0)
    assert subscore(band_lo - step, metric, "male") == pytest.approx(0.5)
    assert subscore(band_lo - 4.0 * step, metric, "male") == 0.0


def test_aggregate_inside_every_band_gives_the_top_score():
    values = {metric["id"]: metric["ideal"]["male"] for metric in metrics_by_group(CALIBRATION, "frontal")}
    values["skin"] = 100.0
    values["symmetry"] = 100.0
    result = aggregate(values, "frontal", "male")
    assert result["quality"] == pytest.approx(1.0)
    assert result["psl"] >= 9.0


def test_pose_estimate_finite():
    landmarks = ideal_face()
    image_shape = (400, 400)
    yaw, pitch, roll = estimate_pose(landmarks, image_shape)
    assert all(np.isfinite(v) for v in (yaw, pitch, roll))


def test_pose_roll_matches_eye_line():
    from engine.geometry import rotate_points, face_center

    landmarks = ideal_face()
    center = face_center(landmarks)
    for angle in (-20.0, -10.0, 10.0, 20.0):
        tilted = rotate_points(landmarks, center, angle)
        _, _, roll = estimate_pose(tilted, (400, 400))
        assert roll == pytest.approx(angle, abs=0.5)


def test_pose_roll_near_zero_for_frontal():
    landmarks = ideal_face()
    _, _, roll = estimate_pose(landmarks, (400, 400))
    assert abs(roll) < 1.0


def test_normalize_does_not_expand_width_without_reliable_yaw():
    landmarks = tilted_face(yaw_scale=0.7)
    image_shape = (400, 400)
    yaw, pitch, roll = estimate_pose(landmarks, image_shape)
    normalized = normalize_landmarks(landmarks, yaw, pitch, roll)

    assert abs(yaw) < 1.0
    assert distance(normalized[0], normalized[16]) == pytest.approx(distance(landmarks[0], landmarks[16]), abs=0.1)


def test_geometry_angle():
    assert angle_degrees(np.array([0, 0]), np.array([1, 1]), np.array([2, 0])) == pytest.approx(90.0)


def test_build_result_metrics_have_id():
    from engine.pipeline import _build_result

    values = {}
    for metric in metrics_by_group(CALIBRATION, "frontal"):
        values[metric["id"]] = metric["ideal"]["male"]
    values["skin"] = 100.0
    aggregate_result = aggregate(values, "frontal", "male")

    result = _build_result(
        "frontal", "male", values, aggregate_result,
        warnings=[], pose={}, lighting={},
    )
    for metric_id, metric in result["metrics"].items():
        assert metric["id"] == metric_id
        assert metric["name_ru"]
        assert metric["points"] > 0


def test_measurements_apply_only_the_declared_landmark_corrections():
    landmarks = ideal_face()
    values = compute_frontal(landmarks, None)
    mouth = midpoint(landmarks[62], landmarks[66])

    raw_esr = distance(*eye_centers(landmarks)) / distance(landmarks[0], landmarks[16])
    assert values["esr"] == pytest.approx(raw_esr * _correction("esr")["scale"], rel=1e-6)

    raw_lip = distance(mouth, landmarks[LIP_LOWER]) / distance(landmarks[LIP_UPPER], mouth)
    assert values["lip_ratio"] == pytest.approx(raw_lip * _correction("lip_ratio")["scale"], rel=1e-6)

    raw_chin = distance(landmarks[LIP_LOWER], landmarks[CHIN]) / distance(landmarks[SUBNASALE], landmarks[LIP_UPPER])
    assert values["chin_philtrum"] == pytest.approx(raw_chin * _correction("chin_philtrum")["scale"], rel=1e-6)

    raw_angle = angle_degrees(landmarks[JAW_GONION_RIGHT], landmarks[CHIN], landmarks[JAW_GONION_LEFT])
    assert values["jfa_angle"] == pytest.approx(raw_angle + _correction("jfa_angle")["offset"], rel=1e-6)


def test_uncorrected_metrics_stay_raw():
    landmarks = ideal_face()
    values = compute_frontal(landmarks, None)
    mouth_width = distance(landmarks[48], landmarks[54])
    assert values["mouth_aspect_ratio"] == pytest.approx(
        distance(landmarks[51], landmarks[57]) / mouth_width, rel=1e-6
    )
    for metric in CALIBRATION["metrics"]:
        assert set(metric["landmark_correction"]) <= {"scale", "offset"}


def test_total_face_ratio_is_height_over_width():
    landmarks = ideal_face()
    hairline = np.array([100.0, 10.0])
    values = compute_frontal(landmarks, hairline)
    correction = CALIBRATION["scale"]["hairline_correction"]
    raw = distance(hairline, landmarks[8]) / face_width(landmarks)
    assert values["tfwhr"] == pytest.approx(raw * correction, rel=1e-6)
    assert values["tfwhr"] > 1.0


def test_the_same_hairline_correction_drives_the_lower_third():
    landmarks = ideal_face()
    hairline = np.array([100.0, 10.0])
    values = compute_frontal(landmarks, hairline)
    correction = CALIBRATION["scale"]["hairline_correction"]
    raw = distance(landmarks[33], landmarks[8]) / distance(hairline, landmarks[8])
    assert values["lower_third_ratio"] == pytest.approx(raw / correction, rel=1e-6)


def test_the_angle_deviation_is_taken_after_the_corrections():
    landmarks = ideal_face()
    values = compute_frontal(landmarks, None)
    assert values["iaa_jfa_deviation"] == pytest.approx(abs(values["iaa_angle"] - values["jfa_angle"]))
