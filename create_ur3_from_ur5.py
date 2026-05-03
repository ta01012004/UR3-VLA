"""
create_ur3_from_ur5.py

Helper script to set up UR3 support in RLBench by:
1. Locating the RLBench installation path
2. Copying ur5.ttm as a base for ur3.ttm (dry-run by default)
3. Patching rlbench/const.py to add UR3 to SUPPORTED_ROBOTS
4. Printing a checklist of manual steps to complete in CoppeliaSim

Usage:
    python create_ur3_from_ur5.py           # dry-run (no changes made)
    python create_ur3_from_ur5.py --apply   # actually apply changes
"""
import argparse
import importlib
import importlib.util
import os
import re
import shutil
import sys
from pathlib import Path
# ---------------------------------------------------------------------------
# 1. Locate RLBench
# ---------------------------------------------------------------------------
def find_rlbench_path() -> Path | None:
    """Return the root directory of the installed rlbench package, or None."""
    # Strategy A: importlib
    spec = importlib.util.find_spec("rlbench")
    if spec is not None and spec.origin is not None:
        p = Path(spec.origin).parent
        print(f"[find_rlbench_path] Found via importlib: {p}")
        return p

    # Strategy B: pip show
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "rlbench"],
            capture_output=True, text=True, timeout=15
        )
        for line in result.stdout.splitlines():
            if line.startswith("Location:"):
                location = line.split(":", 1)[1].strip()
                candidate = Path(location) / "rlbench"
                if candidate.exists():
                    print(f"[find_rlbench_path] Found via pip show: {candidate}")
                    return candidate
    except Exception as e:
        print(f"[find_rlbench_path] pip show failed: {e}")
    # Strategy C: common editable-install locations relative to cwd
    search_roots = [
        Path.cwd(),
        Path.cwd().parent,
        Path.home(),
    ]
    for root in search_roots:
        candidate = root / "rlbench"
        if (candidate / "__init__.py").exists():
            print(f"[find_rlbench_path] Found via filesystem search: {candidate}")
            return candidate

    print("[find_rlbench_path] ERROR: Could not locate rlbench package.")
    return None
# ---------------------------------------------------------------------------
# 2. Locate robot_ttms directory
# ---------------------------------------------------------------------------

def find_robot_ttms_dir(rlbench_path: Path | None = None) -> Path | None:
    """Return the path to rlbench/robot_ttms/, or None if not found."""
    if rlbench_path is None:
        rlbench_path = find_rlbench_path()
    if rlbench_path is None:
        return None

    candidate = rlbench_path / "robot_ttms"
    if candidate.exists():
        print(f"[find_robot_ttms_dir] robot_ttms dir: {candidate}")
        ttm_files = sorted(candidate.glob("*.ttm"))
        print(f"[find_robot_ttms_dir] Existing .ttm files ({len(ttm_files)}):")
        for f in ttm_files:
            print(f"    {f.name}")
        return candidate

    # Fallback: walk up from rlbench_path
    for parent in [rlbench_path, rlbench_path.parent]:
        for dirpath, dirnames, filenames in os.walk(parent):
            if "robot_ttms" in dirnames:
                found = Path(dirpath) / "robot_ttms"
                print(f"[find_robot_ttms_dir] Found via walk: {found}")
                return found

    print("[find_robot_ttms_dir] ERROR: robot_ttms directory not found.")
    return None


# ---------------------------------------------------------------------------
# 3. Copy ur5.ttm -> ur3.ttm
# ---------------------------------------------------------------------------

def copy_ur5_as_ur3(apply: bool = False) -> bool:
    """
    Copy ur5.ttm to ur3.ttm in the robot_ttms directory.

    Parameters
    ----------
    apply : bool
        If False (default) perform a dry-run; if True actually copy the file.

    Returns
    -------
    bool
        True if the operation succeeded (or would succeed in dry-run).
    """
    ttms_dir = find_robot_ttms_dir()
    if ttms_dir is None:
        print("[copy_ur5_as_ur3] FAIL: robot_ttms directory not found.")
        return False

    src = ttms_dir / "ur5.ttm"
    dst = ttms_dir / "ur3.ttm"

    if not src.exists():
        print(f"[copy_ur5_as_ur3] FAIL: Source file not found: {src}")
        return False

    if dst.exists():
        print(f"[copy_ur5_as_ur3] NOTE: {dst.name} already exists at {dst}")
        print("[copy_ur5_as_ur3] Skipping copy (file already present).")
        return True

    if apply:
        shutil.copy2(src, dst)
        print(f"[copy_ur5_as_ur3] DONE: Copied {src.name} -> {dst.name}")
        print(f"    src : {src}")
        print(f"    dst : {dst}")
        print("  IMPORTANT: The copied .ttm is still a UR5 model.")
        print("  You MUST edit ur3.ttm in CoppeliaSim to match UR3 geometry.")
    else:
        print("[copy_ur5_as_ur3] DRY-RUN: Would copy:")
        print(f"    src : {src}")
        print(f"    dst : {dst}")
        print("  Run with --apply to perform the actual copy.")

    return True


# ---------------------------------------------------------------------------
# 4. Patch rlbench/const.py
# ---------------------------------------------------------------------------

_UR3_SNIPPET = "    'ur3',\n"

def patch_const_py(apply: bool = False) -> bool:
    """
    Add 'ur3' to the SUPPORTED_ROBOTS list in rlbench/const.py.

    A backup (.bak) is created before any modification.

    Parameters
    ----------
    apply : bool
        If False (default) perform a dry-run only.

    Returns
    -------
    bool
        True if the operation succeeded (or would succeed in dry-run).
    """
    rlbench_path = find_rlbench_path()
    if rlbench_path is None:
        print("[patch_const_py] FAIL: rlbench path not found.")
        return False

    const_py = rlbench_path / "const.py"
    if not const_py.exists():
        print(f"[patch_const_py] FAIL: {const_py} does not exist.")
        return False

    content = const_py.read_text(encoding="utf-8")

    # Check if UR3 is already present
    if re.search(r"['\"]ur3['\"]", content):
        print("[patch_const_py] NOTE: 'ur3' is already present in const.py. No patch needed.")
        return True

    # Locate SUPPORTED_ROBOTS list and find a good insertion point (after 'ur5')
    # Pattern: find 'ur5' entry inside a list
    ur5_pattern = re.compile(r"(['\"]ur5['\"],?\s*\n)")
    match = ur5_pattern.search(content)

    if match is None:
        print("[patch_const_py] WARNING: Could not find 'ur5' entry in SUPPORTED_ROBOTS.")
        print("  Attempting to find SUPPORTED_ROBOTS block and append 'ur3' manually.")
        # Try to find the list opening
        block_match = re.search(r"(SUPPORTED_ROBOTS\s*=\s*\[)", content)
        if block_match is None:
            print("[patch_const_py] FAIL: SUPPORTED_ROBOTS not found in const.py.")
            return False
        # Insert right after the opening bracket
        insert_pos = block_match.end()
        new_content = content[:insert_pos] + "\n" + _UR3_SNIPPET + content[insert_pos:]
    else:
        # Insert ur3 right after the ur5 line
        insert_pos = match.end()
        new_content = content[:insert_pos] + _UR3_SNIPPET + content[insert_pos:]

    # Show diff summary
    added_lines = [l for l in new_content.splitlines() if l.strip() in ("'ur3',", "'ur3'")]
    print("[patch_const_py] Planned change: add the following line to SUPPORTED_ROBOTS:")
    for line in added_lines:
        print(f"    + {line}")

    if apply:
        backup = const_py.with_suffix(".py.bak")
        shutil.copy2(const_py, backup)
        print(f"[patch_const_py] Backup saved: {backup}")
        const_py.write_text(new_content, encoding="utf-8")
        print(f"[patch_const_py] DONE: Patched {const_py}")
    else:
        print("[patch_const_py] DRY-RUN: No changes written.")
        print("  Run with --apply to apply the patch.")

    return True


# ---------------------------------------------------------------------------
# 5. CoppeliaSim checklist
# ---------------------------------------------------------------------------

def print_coppelia_checklist() -> None:
    """Print the manual steps required inside CoppeliaSim to finalise UR3."""
    checklist = """
=============================================================
  MANUAL STEPS IN CoppeliaSim (after running with --apply)
=============================================================

The script copied ur5.ttm as ur3.ttm.  That file still contains
the UR5 robot model.  You must adapt it for UR3 inside CoppeliaSim:

  [ ] 1. Open ur3.ttm in CoppeliaSim
         File -> Open model... -> select ur3.ttm

  [ ] 2. Replace UR5 joint parameters with UR3 values
         - Joint lengths / DH parameters differ between UR5 and UR3
         - Update each joint's min/max limits to match UR3 spec:
           Joint 1 (Shoulder Pan)  : -360 / +360 deg
           Joint 2 (Shoulder Lift) : -360 / +360 deg
           Joint 3 (Elbow)         : -360 / +360 deg
           Joint 4 (Wrist 1)       : -360 / +360 deg
           Joint 5 (Wrist 2)       : -360 / +360 deg
           Joint 6 (Wrist 3)       : -360 / +360 deg

  [ ] 3. Update visual / collision meshes
         - Import UR3 URDF or individual mesh files (STL/OBJ)
           available at: https://github.com/ros-industrial/universal_robot
         - Replace each link's Shape with the corresponding UR3 mesh

  [ ] 4. Rename the model root object to "UR3" (or "ur3")
         so that RLBench can identify it correctly

  [ ] 5. Verify the TCP (Tool Centre Point) / tip dummy
         - Position must match UR3 end-effector frame

  [ ] 6. Save the model
         File -> Save model as... -> robot_ttms/ur3.ttm
         (overwrite the placeholder copy)

  [ ] 7. (Optional) Add UR3-specific gripper .ttm if needed
         Check rlbench/robot_ttms/ for existing gripper models

  [ ] 8. Test in RLBench
         from rlbench.environment import Environment
         from rlbench.action_modes.action_mode import MoveArmThenGripper
         from rlbench.action_modes.arm_action_modes import JointVelocity
         from rlbench.action_modes.gripper_action_modes import Discrete
         env = Environment(MoveArmThenGripper(JointVelocity(), Discrete()),
                           robot_setup='ur3')
         env.launch()

=============================================================
"""
    print(checklist)


# ---------------------------------------------------------------------------
# 6. Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up UR3 support in RLBench (dry-run by default)."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Actually apply changes (copy file and patch const.py). "
             "Without this flag the script performs a dry-run only.",
    )
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print("=" * 60)
    print(f"  create_ur3_from_ur5.py  |  mode: {mode}")
    print("=" * 60)
    print()

    # Step 1 & 2: locate paths
    rlbench_path = find_rlbench_path()
    print()
    ttms_dir = find_robot_ttms_dir(rlbench_path)
    print()

    # Step 3: copy ur5.ttm -> ur3.ttm
    print("-" * 60)
    print("STEP 1: Copy ur5.ttm as ur3.ttm")
    print("-" * 60)
    copy_ok = copy_ur5_as_ur3(apply=args.apply)
    print()

    # Step 4: patch const.py
    print("-" * 60)
    print("STEP 2: Patch rlbench/const.py (add UR3 to SUPPORTED_ROBOTS)")
    print("-" * 60)
    patch_ok = patch_const_py(apply=args.apply)
    print()

    # Step 5: checklist
    print_coppelia_checklist()

    # Summary
    print("-" * 60)
    print("SUMMARY")
    print("-" * 60)
    print(f"  RLBench path  : {rlbench_path or 'NOT FOUND'}")
    print(f"  robot_ttms dir: {ttms_dir or 'NOT FOUND'}")
    print(f"  Copy step     : {'OK' if copy_ok else 'FAILED'}")
    print(f"  Patch step    : {'OK' if patch_ok else 'FAILED'}")
    if not args.apply:
        print()
        print("  This was a DRY-RUN. No files were modified.")
        print("  Re-run with --apply to apply all changes.")
    print("-" * 60)


if __name__ == "__main__":
    main()
