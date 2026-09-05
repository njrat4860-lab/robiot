import numpy as np

from engine.constants import RIGHT_EYE, LEFT_EYE


def distance(a, b):
    return float(np.linalg.norm(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)))


def midpoint(a, b):
    return (np.asarray(a, dtype=np.float64) + np.asarray(b, dtype=np.float64)) / 2.0


def angle_degrees(p0, p1, p2):
    a = np.asarray(p0, dtype=np.float64)
    b = np.asarray(p1, dtype=np.float64)
    c = np.asarray(p2, dtype=np.float64)
    ba = a - b
    bc = c - b
    denom = np.linalg.norm(ba) * np.linalg.norm(bc)
    if denom == 0:
        return 0.0
    cosine = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def line_angle_degrees(a, b):
    d = np.asarray(b, dtype=np.float64) - np.asarray(a, dtype=np.float64)
    return float(np.degrees(np.arctan2(d[1], d[0])))


def signed_line_angle(a, b):
    return line_angle_degrees(a, b)


def rotate_points(points, center, angle_deg):
    theta = np.radians(angle_deg)
    c = np.cos(theta)
    s = np.sin(theta)
    pts = np.asarray(points, dtype=np.float64) - np.asarray(center, dtype=np.float64)
    rotated = np.column_stack((pts[:, 0] * c - pts[:, 1] * s, pts[:, 0] * s + pts[:, 1] * c))
    return rotated + np.asarray(center, dtype=np.float64)


def eye_centers(landmarks):
    return np.mean(landmarks[RIGHT_EYE], axis=0), np.mean(landmarks[LEFT_EYE], axis=0)


def face_center(landmarks):
    return np.mean(landmarks, axis=0)


def normalize_to_unit(landmarks):
    pts = np.asarray(landmarks, dtype=np.float64)
    center = pts.mean(axis=0)
    centered = pts - center
    scale = np.linalg.norm(centered, axis=1).max()
    if scale == 0:
        return centered
    return centered / scale
