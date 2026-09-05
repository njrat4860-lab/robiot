import bz2
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(ROOT / "models")))
PREDICTOR_NAME = "shape_predictor_68_face_landmarks.dat"
MMOD_NAME = "mmod_human_face_detector.dat"
PREDICTOR_URL = "https://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"


def ensure_models(force=False):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    destination = MODELS_DIR / PREDICTOR_NAME
    if force or not destination.exists() or destination.stat().st_size == 0:
        _download(PREDICTOR_URL, destination)


def _download(url, destination):
    archive = destination.with_suffix(destination.suffix + ".bz2")
    urllib.request.urlretrieve(url, archive)
    with bz2.open(archive, "rb") as source, open(destination, "wb") as target:
        target.write(source.read())
    archive.unlink(missing_ok=True)


def predictor_path():
    return str(MODELS_DIR / PREDICTOR_NAME)


def mmod_path():
    path = MODELS_DIR / MMOD_NAME
    return str(path) if path.exists() else None
