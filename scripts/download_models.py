import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.models import MODELS_DIR, PREDICTOR_NAME, PREDICTOR_URL, _download

MODELS = {PREDICTOR_NAME: PREDICTOR_URL}


def main():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(MODELS)
    for name in targets:
        if name not in MODELS:
            print(f"неизвестная модель: {name}")
            continue
        destination = MODELS_DIR / name
        if destination.exists() and destination.stat().st_size > 0:
            print(f"есть: {name}")
            continue
        print(f"качаю: {name}")
        _download(MODELS[name], destination)
        print(f"готово: {name}")


if __name__ == "__main__":
    main()
