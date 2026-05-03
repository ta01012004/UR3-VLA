"""Small runtime patch to let this RLBench install try robot_setup='ur3'.

PyRep ships a UR3 arm wrapper and CoppeliaSim ships a UR3 model, but this
RLBench release does not register UR3 in SUPPORTED_ROBOTS and does not include
robot_ttms/ur3.ttm. This helper wires those two pieces together for smoke tests.

Important: this is only a first integration step. The CoppeliaSim built-in UR3
model may still need a compatible gripper, wrist camera, tip dummy, and waypoint
alignment before all RLBench tasks work robustly.
"""
from pathlib import Path
import shutil

import rlbench
import rlbench.const as rlbench_const
import rlbench.environment as rlbench_environment
from pyrep.robots.arms.ur3 import UR3
from pyrep.robots.end_effectors.robotiq85_gripper import Robotiq85Gripper


def enable_ur3_robot_setup(coppeliasim_root=None):
    rlbench_root = Path(rlbench.__file__).resolve().parent
    robot_ttms_dir = rlbench_root / "robot_ttms"
    ur3_target = robot_ttms_dir / "ur3.ttm"

    if not ur3_target.exists():
        if coppeliasim_root is None:
            raise FileNotFoundError(
                "robot_ttms/ur3.ttm is missing and COPPELIASIM_ROOT was not set."
            )
        ur3_source = Path(coppeliasim_root) / "models" / "robots" / "non-mobile" / "UR3.ttm"
        if not ur3_source.exists():
            raise FileNotFoundError(f"Could not find CoppeliaSim UR3 model: {ur3_source}")
        shutil.copyfile(ur3_source, ur3_target)

    # environment.py imports SUPPORTED_ROBOTS from rlbench.const; mutate both
    # names to be explicit if a future version stops sharing the same dict.
    rlbench_const.SUPPORTED_ROBOTS["ur3"] = (UR3, Robotiq85Gripper, 6)
    rlbench_environment.SUPPORTED_ROBOTS["ur3"] = (UR3, Robotiq85Gripper, 6)
    return str(ur3_target)
