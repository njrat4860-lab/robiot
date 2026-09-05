import numpy as np

JAW = list(range(0, 17))
RIGHT_BROW = list(range(17, 22))
LEFT_BROW = list(range(22, 27))
NOSE_BRIDGE = list(range(27, 31))
NOSTRILS = list(range(31, 36))
RIGHT_EYE = list(range(36, 42))
LEFT_EYE = list(range(42, 48))
OUTER_LIP = list(range(48, 60))
INNER_LIP = list(range(60, 68))

CHIN = 8
NASION = 27
NOSE_TIP = 30
SUBNASALE = 33

RIGHT_EYE_OUTER = 36
RIGHT_EYE_INNER = 39
LEFT_EYE_INNER = 42
LEFT_EYE_OUTER = 45

MOUTH_RIGHT = 48
MOUTH_LEFT = 54
LIP_UPPER = 51
LIP_LOWER = 57
STOMION_UPPER = 62
STOMION_LOWER = 66

NOSTRIL_RIGHT = 31
NOSTRIL_LEFT = 35

BROW_INNER_RIGHT = 21
BROW_INNER_LEFT = 22
BROW_OUTER_RIGHT = 17
BROW_OUTER_LEFT = 26

JAW_GONION_RIGHT = 3
JAW_GONION_LEFT = 13
JAW_MID_RIGHT = 5
JAW_MID_LEFT = 11

POSE_MODEL_POINTS = np.array(
    [
        [0.0, 0.0, 0.0],
        [0.0, -330.0, -65.0],
        [-225.0, 170.0, -135.0],
        [225.0, 170.0, -135.0],
        [-150.0, -150.0, -125.0],
        [150.0, -150.0, -125.0],
    ],
    dtype=np.float64,
)

POSE_LANDMARK_IDS = [NOSE_TIP, CHIN, RIGHT_EYE_OUTER, LEFT_EYE_OUTER, MOUTH_RIGHT, MOUTH_LEFT]

SKIN_REFERENCE_WEIGHTS = {"tone": 0.35, "texture": 0.30, "redness": 0.20, "dark_circles": 0.15}
