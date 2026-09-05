import numpy as np
import pytest

from engine.pose import estimate_pose
from tests.synthetic import ideal_face


IMAGE_SHAPE = (400, 400)
MAX_SHIFTED_YAW_DEGREES = 1.0


def test_pose_estimate_does_not_depend_on_face_position_in_the_frame():
    centered = ideal_face()
    shifted = centered.copy()
    shifted[:, 0] -= 50.0

    centered_yaw, _, _ = estimate_pose(centered, IMAGE_SHAPE)
    shifted_yaw, _, _ = estimate_pose(shifted, IMAGE_SHAPE)

    assert abs(shifted_yaw - centered_yaw) <= MAX_SHIFTED_YAW_DEGREES
