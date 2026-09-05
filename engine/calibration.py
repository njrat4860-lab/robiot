import json
from functools import lru_cache
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


@lru_cache(maxsize=None)
def _load(name):
    with open(ASSETS_DIR / name, encoding="utf-8") as file:
        return json.load(file)


def load_calibration():
    return _load("calibration.json")


def load_advice():
    return _load("advice.json")


def metrics_by_group(calibration, group):
    return [m for m in calibration["metrics"] if m["group"] == group or m["group"] == "both"]


def metric_lookup(calibration):
    return {m["id"]: m for m in calibration["metrics"]}
