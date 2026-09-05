import numpy as np

from engine.calibration import load_calibration, metrics_by_group

PSL_FLOOR = 1.0
PSL_CEILING = 10.0
BLOCK_SCALE = 10.0
HALVING_BASE = 0.5
TIER_INSIDE_BAND = 1
BAND_SHAPE = "band"
PERCENT_SHAPE = "percent"
PERCENT_SCALE = 100.0
NON_BAND_TIER_STEPS = 4
UNMEASURED_SCORE = 0.5
TIER_SCORES = {1: 1.0, 2: 0.5, 3: 0.25, 4: 0.125, 5: 0.0}


def band_limits(metric, gender):
    low, high = metric["band"][gender]
    return float(low), float(high)


def tolerance(metric, gender):
    low, high = band_limits(metric, gender)
    return (high - low) / 2.0


def band_offset(value, metric, gender):
    low, high = band_limits(metric, gender)
    if value < low:
        return low - value
    if value > high:
        return value - high
    return 0.0


def offset_in_tolerances(value, metric, gender):
    step = tolerance(metric, gender)
    if step <= 0.0:
        return 0.0
    return band_offset(value, metric, gender) / step


def metric_tier(value, metric, gender):
    if value is None:
        return None
    max_tier = load_calibration()["scale"]["max_tier"]
    if metric.get("shape", BAND_SHAPE) != BAND_SHAPE:
        missing = (1.0 - subscore(value, metric, gender)) * NON_BAND_TIER_STEPS
        return int(min(max_tier, TIER_INSIDE_BAND + int(np.floor(missing))))
    offset = offset_in_tolerances(value, metric, gender)
    return int(min(max_tier, TIER_INSIDE_BAND + int(np.ceil(offset))))


def subscore(value, metric, gender):
    if value is None:
        return None
    if metric.get("shape", BAND_SHAPE) == PERCENT_SHAPE:
        return float(np.clip(value / PERCENT_SCALE, 0.0, 1.0))
    return TIER_SCORES[metric_tier(value, metric, gender)]


def aggregate(values, group, gender, disabled_metrics=None):
    calibration = load_calibration()
    results = _metric_results(calibration, values, group, gender, disabled_metrics or frozenset())
    blocks = _block_scores(results)
    blocks = _blocks_with_priors(blocks, group, calibration)
    psl = _calibrated_psl(_combine_blocks(blocks, calibration["scale"]["block_weights"]), calibration["scale"].get("psl_curve", []))
    quality = blocks.get("harmony", 0.0) / BLOCK_SCALE
    coverage = sum(1 for entry in results.values() if entry["score"] is not None)
    return {"quality": quality, "psl": psl, "results": results, "coverage": coverage, "blocks": blocks}


def deviation_direction(measured, metric, gender):
    if measured is None:
        return None
    low, high = band_limits(metric, gender)
    if measured < low:
        return "low"
    if measured > high:
        return "high"
    return None


def _halving_score(value, metric, gender):
    scale = load_calibration()["scale"]
    offset = offset_in_tolerances(value, metric, gender)
    if offset >= scale["max_tier"] - TIER_INSIDE_BAND:
        return 0.0
    return float(HALVING_BASE ** (offset / scale["tier_halving_step"]))


def _metric_results(calibration, values, group, gender, disabled_metrics):
    results = {}
    for metric in metrics_by_group(calibration, group):
        if metric["id"] in disabled_metrics:
            continue
        metric_id = metric["id"]
        if metric_id not in values:
            continue
        measured = values.get(metric_id)
        results[metric_id] = {
            "measured": measured,
            "score": subscore(measured, metric, gender),
            "tier": metric_tier(measured, metric, gender),
            "points": _earned_points(measured, metric, gender),
            "metric": metric,
        }
    return results


def _earned_points(measured, metric, gender):
    score = subscore(measured, metric, gender)
    if score is None:
        return None
    return float(score * metric["points"])


def _block_scores(results):
    earned = {}
    available = {}
    for entry in results.values():
        block = entry["metric"]["block"]
        available[block] = available.get(block, 0.0) + entry["metric"]["points"]
        if entry["score"] is None:
            earned[block] = earned.get(block, 0.0) + entry["metric"]["points"] * UNMEASURED_SCORE
            continue
        earned[block] = earned.get(block, 0.0) + entry["points"]
    return {
        block: BLOCK_SCALE * earned.get(block, 0.0) / available[block]
        for block in available
        if available[block] > 0.0
    }


def _blocks_with_priors(blocks, group, calibration):
    combined = dict(blocks)
    for block, value in calibration["scale"].get("block_priors", {}).get(group, {}).items():
        combined.setdefault(block, float(value))
    return combined


def _calibrated_psl(value, curve):
    if not curve:
        return value
    points = sorted((float(source), float(target)) for source, target in curve)
    if value <= points[0][0]:
        return points[0][1]
    for left, right in zip(points, points[1:]):
        if value <= right[0]:
            span = right[0] - left[0]
            if span <= 0.0:
                return right[1]
            fraction = (value - left[0]) / span
            return float(left[1] + (right[1] - left[1]) * fraction)
    return points[-1][1]


def _combine_blocks(blocks, block_weights):
    weighted = 0.0
    total = 0.0
    for block, value in blocks.items():
        weight = block_weights.get(block, 0.0)
        weighted += weight * value
        total += weight
    if total <= 0.0:
        return PSL_FLOOR
    return float(np.clip(weighted / total, PSL_FLOOR, PSL_CEILING))
