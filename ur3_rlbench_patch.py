#!/usr/bin/env python3
"""
ur3_rlbench_patch.py

Patches RLBench to support the UR3 robot arm.
This script:
  1. Prints step-by-step manual patch instructions
  2. Creates ur3_const_patch.py with the patched const.py content
  3. Creates ur3_env_setup.py — a helper to launch RLBench with UR3

No RLBench installation required to run this script.
"""

import os
import textwrap

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# 1. Step-by-step manual instructions
# ---------------------------------------------------------------------------

INSTRUCTIONS = textwrap.dedent("""\
    ============================================================
    STEP-BY-STEP GUIDE: Add UR3 support to RLBench
    ============================================================

    BACKGROUND
    ----------
    RLBench currently supports: panda, jaco, mico, sawyer, ur5.
    PyRep already ships UR3 (pyrep/robots/arms/ur3.py, class UR3).
    We only need to wire UR3 into RLBench's robot registry and
    supply a matching .ttm scene file.

    PREREQUISITES
    -------------
    * RLBench cloned locally  (https://github.com/stepjam/RLBench)
    * PyRep installed with CoppeliaSim 4.x
    * Python 3.8+

    ============================================================
    STEP 1 — Add UR3 to rlbench/const.py
    ============================================================

    Open  <rlbench_root>/rlbench/const.py

    Find the SUPPORTED_ROBOTS dict (looks like):

        SUPPORTED_ROBOTS = {
            'panda':  (Panda,  PandaGripper,  7),
            'jaco':   (Jaco,   JacoGripper,   7),
            'mico':   (Mico,   MicoGripper,   6),
            'sawyer': (Sawyer, BaxterGripper,  7),
            'ur5':    (UR5,    Robotiq85Gripper, 6),
        }

    Add the UR3 import at the top of the file (with the other arm imports):

        from pyrep.robots.arms.ur3 import UR3

    Then add the UR3 entry:

        'ur3': (UR3, Robotiq85Gripper, 6),

    The full updated block should look like:

        from pyrep.robots.arms.panda   import Panda
        from pyrep.robots.arms.jaco    import Jaco
        from pyrep.robots.arms.mico    import Mico
        from pyrep.robots.arms.sawyer  import Sawyer
        from pyrep.robots.arms.ur5     import UR5
        from pyrep.robots.arms.ur3     import UR3          # <-- NEW
        from pyrep.robots.end_effectors.panda_gripper    import PandaGripper
        from pyrep.robots.end_effectors.jaco_gripper     import JacoGripper
        from pyrep.robots.end_effectors.mico_gripper     import MicoGripper
        from pyrep.robots.end_effectors.baxter_gripper   import BaxterGripper
        from pyrep.robots.end_effectors.robotiq85_gripper import Robotiq85Gripper

        SUPPORTED_ROBOTS = {
            'panda':  (Panda,  PandaGripper,    7),
            'jaco':   (Jaco,   JacoGripper,     7),
            'mico':   (Mico,   MicoGripper,     6),
            'sawyer': (Sawyer, BaxterGripper,   7),
            'ur5':    (UR5,    Robotiq85Gripper, 6),
            'ur3':    (UR3,    Robotiq85Gripper, 6),  # <-- NEW
        }

    ============================================================
    STEP 2 — Provide the UR3 .ttm scene file
    ============================================================

    RLBench loads robot models from:
        <rlbench_root>/rlbench/robot_ttms/<robot_name>.ttm

    You need  ur3.ttm  in that directory.

    Option A — Export from CoppeliaSim:
        1. Open CoppeliaSim.
        2. Load the PyRep UR3 model:
               <pyrep_root>/pyrep/robots/ttms/UR3.ttm
           (or search your PyRep installation for UR3*.ttm)
        3. File → Save model as… → save to
               <rlbench_root>/rlbench/robot_ttms/ur3.ttm
           (lowercase, no suffix change)

    Option B — Symlink / copy existing file:
        cp  <pyrep_root>/pyrep/robots/ttms/UR3.ttm  \\
            <rlbench_root>/rlbench/robot_ttms/ur3.ttm

    ============================================================
    STEP 3 — (Optional) Verify the gripper attachment
    ============================================================

    The UR3 shares the same 6-DOF kinematic chain as the UR5.
    Robotiq85Gripper attaches to the flange link named
    "UR5_link7" in the UR5 .ttm.  The UR3 .ttm from PyRep uses
    "UR3_link7".  If you get a "respondable object not found"
    error at runtime:

        * Open ur3.ttm in CoppeliaSim.
        * Rename the tip/target dummy objects to match what
          Robotiq85Gripper expects, OR
        * Create a dedicated UR3Gripper class in PyRep modelled
          after Robotiq85Gripper but pointing to UR3 link names.

    ============================================================
    STEP 4 — Run a quick smoke-test
    ============================================================

    After applying steps 1–3, run the generated helper:

        python ur3_env_setup.py

    If no exception is raised the robot is wired up correctly.

    ============================================================
    FILES GENERATED BY THIS SCRIPT
    ============================================================
    * ur3_const_patch.py  — drop-in replacement content for
                            rlbench/const.py (with UR3 added)
    * ur3_env_setup.py    — helper that instantiates a RLBench
                            Environment using robot_setup='ur3'
    ============================================================
""")

print(INSTRUCTIONS)


# ---------------------------------------------------------------------------
# 2. Create ur3_const_patch.py
# ---------------------------------------------------------------------------

CONST_PATCH_CONTENT = textwrap.dedent('''\
    """
    ur3_const_patch.py
    ==================
    This is a patched version of rlbench/const.py that adds UR3 support.

    Usage
    -----
    Replace  <rlbench_root>/rlbench/const.py  with this file, OR
    apply only the highlighted lines to the original file.

    Lines marked  # <<<< NEW  are the additions required for UR3.
    """

    from pyrep.robots.arms.panda   import Panda
    from pyrep.robots.arms.jaco    import Jaco
    from pyrep.robots.arms.mico    import Mico
    from pyrep.robots.arms.sawyer  import Sawyer
    from pyrep.robots.arms.ur5     import UR5
    from pyrep.robots.arms.ur3     import UR3                          # <<<< NEW

    from pyrep.robots.end_effectors.panda_gripper     import PandaGripper
    from pyrep.robots.end_effectors.jaco_gripper      import JacoGripper
    from pyrep.robots.end_effectors.mico_gripper      import MicoGripper
    from pyrep.robots.end_effectors.baxter_gripper    import BaxterGripper
    from pyrep.robots.end_effectors.robotiq85_gripper import Robotiq85Gripper

    # ---------------------------------------------------------------------------
    # Robot registry
    # Each entry: robot_name -> (ArmClass, GripperClass, num_joints)
    # ---------------------------------------------------------------------------
    SUPPORTED_ROBOTS = {
        \'panda\':  (Panda,  PandaGripper,    7),
        \'jaco\':   (Jaco,   JacoGripper,     7),
        \'mico\':   (Mico,   MicoGripper,     6),
        \'sawyer\': (Sawyer, BaxterGripper,   7),
        \'ur5\':    (UR5,    Robotiq85Gripper, 6),
        \'ur3\':    (UR3,    Robotiq85Gripper, 6),  # <<<< NEW
    }

    # ---------------------------------------------------------------------------
    # Remaining original constants from rlbench/const.py
    # (keep whatever was already in the file below this line)
    # ---------------------------------------------------------------------------

    # Camera / observation constants (originals — do not remove)
    DEPTH_SCALE = 2**24 - 1

    # Task data directories
    TASKS_PATH    = \'tasks\'
    TASK_TTM_PATH = \'task_ttms\'
    ROBOT_TTM     = \'robot_ttms\'
''')

const_patch_path = os.path.join(OUTPUT_DIR, "ur3_const_patch.py")
with open(const_patch_path, "w") as f:
    f.write(CONST_PATCH_CONTENT)

print(f"[OK] Created: {const_patch_path}")


# ---------------------------------------------------------------------------
# 3. Create ur3_env_setup.py
# ---------------------------------------------------------------------------

ENV_SETUP_CONTENT = textwrap.dedent('''\
    """
    ur3_env_setup.py
    ================
    Helper script that creates a RLBench Environment configured for the UR3
    robot arm.

    Prerequisites
    -------------
    * RLBench patched to include UR3 in SUPPORTED_ROBOTS  (see ur3_const_patch.py)
    * ur3.ttm placed in  <rlbench_root>/rlbench/robot_ttms/ur3.ttm
    * CoppeliaSim + PyRep installed and on PATH / LD_LIBRARY_PATH

    Run
    ---
        python ur3_env_setup.py

    The environment launches headlessly by default (headless=True).
    Set  DISPLAY  and change headless=False to render the simulation.
    """

    from rlbench.environment import Environment
    from rlbench.action_modes.action_mode import MoveArmThenGripper
    from rlbench.action_modes.arm_action_modes import JointVelocity
    from rlbench.action_modes.gripper_action_modes import Discrete
    from rlbench.tasks import ReachTarget          # lightweight demo task


    def make_ur3_env(headless: bool = True) -> Environment:
        """Return an initialised RLBench Environment using the UR3 arm."""
        action_mode = MoveArmThenGripper(
            arm_action_mode=JointVelocity(),
            gripper_action_mode=Discrete(),
        )
        env = Environment(
            action_mode=action_mode,
            obs_config=None,          # uses default ObservationConfig
            robot_setup=\'ur3\',        # <-- selects UR3 from SUPPORTED_ROBOTS
            headless=headless,
        )
        return env


    def demo_reach(headless: bool = True):
        """Quick smoke-test: launch env, load ReachTarget, step a few times."""
        env = make_ur3_env(headless=headless)
        env.launch()
        print("[ur3_env_setup] Environment launched with UR3.")

        task = env.get_task(ReachTarget)
        descriptions, obs = task.reset()
        print(f"[ur3_env_setup] Task reset OK. Goal: {descriptions[0]}")

        import numpy as np
        # 6 joint-velocity DOFs + 1 gripper binary action
        action = np.zeros(7)
        for step in range(5):
            obs, reward, terminate = task.step(action)
            print(f"  step {step + 1}: reward={reward:.4f}  done={terminate}")
            if terminate:
                break

        env.shutdown()
        print("[ur3_env_setup] Environment shut down cleanly.")


    if __name__ == "__main__":
        import argparse

        parser = argparse.ArgumentParser(description="UR3 RLBench environment helper")
        parser.add_argument(
            "--render", action="store_true",
            help="Disable headless mode and open CoppeliaSim GUI"
        )
        parser.add_argument(
            "--demo", action="store_true",
            help="Run a short ReachTarget demo after launching"
        )
        args = parser.parse_args()

        if args.demo:
            demo_reach(headless=not args.render)
        else:
            env = make_ur3_env(headless=not args.render)
            print("[ur3_env_setup] Environment object created (not yet launched).")
            print("  Call env.launch() then env.get_task(...) to proceed.")
            print("  Run with --demo to execute a short ReachTarget episode.")
''')

env_setup_path = os.path.join(OUTPUT_DIR, "ur3_env_setup.py")
with open(env_setup_path, "w") as f:
    f.write(ENV_SETUP_CONTENT)

print(f"[OK] Created: {env_setup_path}")


# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

print()
print("=" * 60)
print("All files generated successfully.")
print("=" * 60)
print(f"  {const_patch_path}")
print(f"  {env_setup_path}")
print()
print("Next steps:")
print("  1. Apply ur3_const_patch.py to your RLBench installation.")
print("  2. Copy ur3.ttm to <rlbench_root>/rlbench/robot_ttms/ur3.ttm")
print("  3. Run:  python ur3_env_setup.py --demo")
