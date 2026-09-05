import numpy as np

MIN_CLIPPED_PIXELS = 0.08
EXTREME_CLIPPED_PIXELS = 0.18
MIN_DARK_SIDE = 0.035
MIN_LIGHT_SIDE = 0.035


def analyze(image_gray):
    gray = np.asarray(image_gray, dtype=np.uint8)
    if gray.ndim == 3:
        gray = gray[..., :3].mean(axis=2).astype(np.uint8)
    brightness = float(gray.mean())
    contrast = float(gray.std())
    total = float(gray.size)
    dark = float((gray <= 5).sum()) / total if total else 0.0
    light = float((gray >= 250).sum()) / total if total else 0.0
    clipped = dark + light
    return {"brightness": brightness, "contrast": contrast, "clipped": clipped, "dark_clipped": dark, "light_clipped": light}


def assess(lighting, limits):
    problems = []
    if lighting["brightness"] < limits["min_brightness"]:
        problems.append("слишком тёмное фото")
    if lighting["brightness"] > limits["max_brightness"]:
        problems.append("пересвеченное фото")
    if lighting["contrast"] < limits["min_contrast"]:
        problems.append("низкий контраст, освещение плоское")
    if _has_clipping_problem(lighting, limits):
        problems.append("сильные засветы или провалы в тенях")
    return problems


def _has_clipping_problem(lighting, limits):
    clipped = lighting["clipped"]
    dark = lighting.get("dark_clipped", 0.0)
    light = lighting.get("light_clipped", 0.0)
    limit = max(float(limits.get("clipped_ratio", 0.04)), MIN_CLIPPED_PIXELS)
    if clipped <= limit:
        return False
    if clipped >= EXTREME_CLIPPED_PIXELS:
        return True
    return dark >= MIN_DARK_SIDE and light >= MIN_LIGHT_SIDE
