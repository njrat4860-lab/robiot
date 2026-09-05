import numpy as np

from engine.constants import POSE_MODEL_POINTS, POSE_LANDMARK_IDS, RIGHT_EYE_OUTER, LEFT_EYE_OUTER
from engine.geometry import face_center, rotate_points, distance, midpoint


def estimate_pose(landmarks, image_shape):
    yaw, pitch, roll, _ = estimate_pose_with_matrix(landmarks, image_shape)
    return yaw, pitch, roll


def estimate_pose_with_matrix(landmarks, image_shape):
    height, width = image_shape[:2]
    image_points = np.asarray(landmarks[POSE_LANDMARK_IDS], dtype=np.float64)
    model_points = np.asarray(POSE_MODEL_POINTS, dtype=np.float64)
    rotation_matrix = _solve_rotation(model_points, image_points, width, height)
    yaw, pitch, _ = _decompose(rotation_matrix)
    roll = _roll_from_eyes(landmarks)
    return float(yaw), float(pitch), float(roll), rotation_matrix


def _roll_from_eyes(landmarks):
    left = np.asarray(landmarks[LEFT_EYE_OUTER], dtype=np.float64)
    right = np.asarray(landmarks[RIGHT_EYE_OUTER], dtype=np.float64)
    return float(np.degrees(np.arctan2(left[1] - right[1], left[0] - right[0])))


def _solve_rotation(model_points, image_points, width, height):
    focal = float(max(width, height))
    cx = float(np.mean(image_points[:, 0]))
    cy = float(np.mean(image_points[:, 1]))
    K = np.array(
        [[focal, 0.0, cx], [0.0, focal, cy], [0.0, 0.0, 1.0]],
        dtype=np.float64,
    )
    count = model_points.shape[0]
    equations = np.zeros((2 * count, 12), dtype=np.float64)
    for i in range(count):
        x, y, z = model_points[i]
        u, v = image_points[i]
        equations[2 * i] = [x, y, z, 1.0, 0, 0, 0, 0, -u * x, -u * y, -u * z, -u]
        equations[2 * i + 1] = [0, 0, 0, 0, x, y, z, 1.0, -v * x, -v * y, -v * z, -v]
    _, _, vt = np.linalg.svd(equations)
    projection = vt[-1].reshape(3, 4)
    extrinsic = np.linalg.solve(K, projection)
    approximate = extrinsic[:, :3]
    u_mat, _, v_mat = np.linalg.svd(approximate)
    rotation = u_mat @ v_mat
    if np.linalg.det(rotation) < 0.0:
        v_mat[-1] *= -1.0
        rotation = u_mat @ v_mat
    return rotation


def _decompose(rotation_matrix):
    sy = np.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
    yaw = np.degrees(np.arctan2(-rotation_matrix[2, 0], sy))
    roll = np.degrees(np.arctan2(rotation_matrix[1, 0], rotation_matrix[0, 0]))
    pitch = np.degrees(np.arctan2(rotation_matrix[2, 1], rotation_matrix[2, 2]))
    if pitch > 90.0:
        pitch -= 180.0
    elif pitch < -90.0:
        pitch += 180.0
    return float(yaw), float(pitch), float(roll)


def normalize_landmarks(landmarks, yaw, pitch, roll, rotation_matrix=None):
    return normalize_points(landmarks, landmarks, yaw, pitch, roll, rotation_matrix)


def normalize_points(points, reference_landmarks, yaw, pitch, roll, rotation_matrix=None):
    points = np.asarray(points, dtype=np.float64)
    center = face_center(reference_landmarks)
    derolled = rotate_points(points, center, -roll)
    centered = derolled - center
    yaw_factor = 1.0 / max(np.cos(np.radians(yaw)), 0.35)
    pitch_factor = 1.0 / max(np.cos(np.radians(pitch)), 0.35)
    corrected = np.column_stack((centered[:, 0] * yaw_factor, centered[:, 1] * pitch_factor))
    return corrected + center


def is_frontal(yaw, pitch, roll, limits):
    return (
        abs(yaw) <= limits["max_yaw_deg"]
        and abs(pitch) <= limits["max_pitch_deg"]
        and abs(roll) <= limits["max_roll_deg"]
    )


def pose_warnings(yaw, pitch, roll, limits):
    warnings = []
    if abs(yaw) > limits["warn_yaw_deg"]:
        warnings.append("поворот головы вбок - замеры ширины менее точные")
    if abs(pitch) > limits["warn_pitch_deg"]:
        warnings.append("наклон головы вверх или вниз - замеры высоты менее точные")
    if abs(roll) > limits["warn_roll_deg"]:
        warnings.append("наклон головы в сторону выправлен")
    return warnings


def detect_emotion_warnings(landmarks):
    warnings = []
    ear = _eye_aspect_ratio(landmarks)
    mar = _mouth_aspect_ratio(landmarks)
    smile = _smile_ratio(landmarks)
    if ear is not None and ear < 0.18:
        warnings.append("глаза прикрыты - открой глаза и смотри прямо")
    if mar is not None and mar > 0.45:
        warnings.append("рот открыт - держи губы сомкнутыми нейтрально")
    if smile is not None and smile > 1.85:
        warnings.append("улыбка искажает пропорции - сделай нейтральное лицо")
    return warnings


def emotion_metrics(landmarks):
    return {
        "eye_aspect": _eye_aspect_ratio(landmarks),
        "mouth_aspect": _mouth_aspect_ratio(landmarks),
        "smile_ratio": _smile_ratio(landmarks),
    }


def _eye_aspect_ratio(landmarks):
    try:
        right_top = midpoint(landmarks[37], landmarks[38])
        right_bot = midpoint(landmarks[40], landmarks[41])
        left_top = midpoint(landmarks[43], landmarks[44])
        left_bot = midpoint(landmarks[46], landmarks[47])
        right_h = distance(right_top, right_bot)
        left_h = distance(left_top, left_bot)
        right_w = distance(landmarks[36], landmarks[39])
        left_w = distance(landmarks[42], landmarks[45])
        if right_w == 0 or left_w == 0:
            return None
        return float((right_h / right_w + left_h / left_w) / 2.0)
    except Exception:
        return None


def _mouth_aspect_ratio(landmarks):
    try:
        top = landmarks[51]
        bottom = landmarks[57]
        left = landmarks[48]
        right = landmarks[54]
        inner_top = landmarks[62]
        inner_bottom = landmarks[66]
        h_outer = distance(top, bottom)
        h_inner = distance(inner_top, inner_bottom)
        w = distance(left, right)
        if w == 0:
            return None
        return float(max(h_outer, h_inner) / w)
    except Exception:
        return None


def _smile_ratio(landmarks):
    try:
        mouth_w = distance(landmarks[48], landmarks[54])
        nose_w = distance(landmarks[31], landmarks[35]) * 1.25
        if nose_w == 0:
            return None
        return float(mouth_w / nose_w)
    except Exception:
        return None
