#!/usr/bin/env python3
"""
test_ur3_env.py
Test script to verify UR3 environment setup for RLBench + CoppeliaSim/PyRep.
Gracefully handles missing dependencies and prints clear pass/fail summary.
"""

import sys
import os

results = {}

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────

def ok(label, msg=""):
    tag = "✓"
    results[label] = True
    print(f"  {tag} PASS  {label}" + (f": {msg}" if msg else ""))

def fail(label, msg=""):
    tag = "✗"
    results[label] = False
    print(f"  {tag} FAIL  {label}" + (f": {msg}" if msg else ""))


# ──────────────────────────────────────────────────────────────────────────────
# Test 1 — Import core modules
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 1 — Import core modules")
print("="*60)

pyrep_available = False
rlbench_available = False

try:
    import pyrep
    version = getattr(pyrep, "__version__", "unknown")
    ok("import pyrep", f"version={version}")
    pyrep_available = True
except ImportError as e:
    fail("import pyrep", str(e))
except Exception as e:
    fail("import pyrep", f"unexpected error: {e}")

try:
    import rlbench
    version = getattr(rlbench, "__version__", "unknown")
    ok("import rlbench", f"version={version}")
    rlbench_available = True
except ImportError as e:
    fail("import rlbench", str(e))
except Exception as e:
    fail("import rlbench", f"unexpected error: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 2 — Import UR3 class from PyRep
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 2 — Import UR3 class from pyrep")
print("="*60)

ur3_class_available = False

if not pyrep_available:
    fail("import UR3 class", "pyrep not available (skipped)")
else:
    try:
        from pyrep.robots.arms.ur3 import UR3
        ok("import UR3 class", f"class={UR3}")
        ur3_class_available = True
    except ImportError as e:
        fail("import UR3 class", str(e))
        print("    --> Hint: UR3 arm module may not exist in this version of PyRep.")
        print("         Check: pyrep/robots/arms/ for available arm classes.")
    except Exception as e:
        fail("import UR3 class", f"unexpected error: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 3 — SUPPORTED_ROBOTS in RLBench
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 3 — SUPPORTED_ROBOTS in RLBench")
print("="*60)

if not rlbench_available:
    fail("SUPPORTED_ROBOTS check", "rlbench not available (skipped)")
    fail("UR3 in SUPPORTED_ROBOTS", "rlbench not available (skipped)")
else:
    try:
        # RLBench stores supported robots in environment or utils
        supported = None
        source = None

        # Try multiple known locations
        try:
            from rlbench.environment import SUPPORTED_ROBOTS
            supported = SUPPORTED_ROBOTS
            source = "rlbench.environment.SUPPORTED_ROBOTS"
        except ImportError:
            pass

        if supported is None:
            try:
                from rlbench import SUPPORTED_ROBOTS
                supported = SUPPORTED_ROBOTS
                source = "rlbench.SUPPORTED_ROBOTS"
            except ImportError:
                pass

        if supported is None:
            # Try to grep for it in the rlbench package dir
            try:
                import rlbench as _rlb
                pkg_dir = os.path.dirname(_rlb.__file__)
                env_file = os.path.join(pkg_dir, "environment.py")
                if os.path.exists(env_file):
                    with open(env_file) as f:
                        content = f.read()
                    # Parse simple dict/list assignment
                    import ast, re
                    match = re.search(r"SUPPORTED_ROBOTS\s*=\s*(\{[^}]+\}|\[[^\]]+\])", content, re.DOTALL)
                    if match:
                        supported = ast.literal_eval(match.group(1))
                        source = f"parsed from {env_file}"
            except Exception:
                pass

        if supported is not None:
            ok("SUPPORTED_ROBOTS check", f"source={source}")
            robot_list = list(supported.keys()) if isinstance(supported, dict) else list(supported)
            print(f"    Supported robots ({len(robot_list)}): {robot_list}")

            if "ur3" in robot_list or "UR3" in robot_list:
                ok("UR3 in SUPPORTED_ROBOTS", "ur3 is officially supported")
            else:
                fail("UR3 in SUPPORTED_ROBOTS",
                     "ur3 NOT in list — needs manual integration")
                print("    --> Hint: To add UR3 support, edit rlbench/environment.py")
                print("         and add an entry to SUPPORTED_ROBOTS dict.")
        else:
            fail("SUPPORTED_ROBOTS check", "could not locate SUPPORTED_ROBOTS in rlbench")
            fail("UR3 in SUPPORTED_ROBOTS", "SUPPORTED_ROBOTS not found (skipped)")

    except Exception as e:
        fail("SUPPORTED_ROBOTS check", f"unexpected error: {e}")
        fail("UR3 in SUPPORTED_ROBOTS", "error during check")


# ──────────────────────────────────────────────────────────────────────────────
# Test 4 — ur3.ttm file exists
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 4 — ur3.ttm model file")
print("="*60)

ttm_found = False

def find_ttm(root, filename):
    """Walk root looking for filename, return first match or None."""
    for dirpath, _dirs, files in os.walk(root):
        if filename in files:
            return os.path.join(dirpath, filename)
    return None

search_roots = []

# 1. site-packages
for p in sys.path:
    if "site-packages" in p and os.path.isdir(p):
        search_roots.append(p)

# 2. rlbench package dir directly
if rlbench_available:
    try:
        import rlbench as _rlb
        search_roots.append(os.path.dirname(_rlb.__file__))
    except Exception:
        pass

# 3. common conda/venv paths
for candidate in [
    "/usr/local/lib",
    os.path.expanduser("~/miniconda3"),
    os.path.expanduser("~/anaconda3"),
    os.path.expanduser("~/.local/lib"),
]:
    if os.path.isdir(candidate):
        search_roots.append(candidate)

searched = set()
ttm_path = None
for root in search_roots:
    if root in searched:
        continue
    searched.add(root)
    result = find_ttm(root, "ur3.ttm")
    if result:
        ttm_path = result
        break

if ttm_path:
    ok("ur3.ttm exists", ttm_path)
    ttm_found = True
else:
    fail("ur3.ttm exists", "file not found in site-packages / rlbench dirs")
    print("    --> Hint: You need to create/copy ur3.ttm into:")
    print("         <rlbench_package>/robot_ttms/ur3.ttm")
    print("         Obtain it from CoppeliaSim model library or create from UR3 URDF.")

# Also check canonical path relative to rlbench package
if rlbench_available and not ttm_found:
    try:
        import rlbench as _rlb
        canonical = os.path.join(os.path.dirname(_rlb.__file__), "robot_ttms", "ur3.ttm")
        print(f"    Expected canonical path: {canonical}")
        if os.path.exists(canonical):
            ok("ur3.ttm canonical path", canonical)
        else:
            fail("ur3.ttm canonical path", f"not found at {canonical}")
    except Exception as e:
        fail("ur3.ttm canonical path", str(e))


# ──────────────────────────────────────────────────────────────────────────────
# Test 5 — Environment initialisation (headless, expect graceful errors)
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("TEST 5 — Environment initialisation with robot_setup='ur3'")
print("="*60)

if not rlbench_available:
    fail("Environment init", "rlbench not available (skipped)")
else:
    try:
        from rlbench.environment import Environment
        from rlbench.action_modes.action_mode import MoveArmThenGripper
        from rlbench.action_modes.arm_action_modes import JointVelocity
        from rlbench.action_modes.gripper_action_modes import Discrete
        from rlbench.observation_config import ObservationConfig

        obs_config = ObservationConfig()
        obs_config.set_all(False)

        action_mode = MoveArmThenGripper(
            arm_action_mode=JointVelocity(),
            gripper_action_mode=Discrete()
        )

        env = Environment(
            action_mode=action_mode,
            obs_config=obs_config,
            headless=True,
            robot_setup="ur3",
        )

        # Try launching — this requires CoppeliaSim running
        try:
            env.launch()
            ok("Environment init", "launched successfully")
            results["Environment init"] = True
            try:
                env.shutdown()
            except Exception:
                pass
        except Exception as launch_err:
            err_str = str(launch_err).lower()
            # Categorise the error
            if "coppeliasim" in err_str or "vrep" in err_str or "pyrep" in err_str or "shared library" in err_str:
                fail("Environment init",
                     "CoppeliaSim/PyRep not reachable — is CoppeliaSim running?")
                print("    --> Fix: Start CoppeliaSim first, then run this script,")
                print("         OR set DISPLAY and COPPELIASIM_ROOT env variables.")
            elif "ur3" in err_str or "robot" in err_str or "ttm" in err_str:
                fail("Environment init",
                     f"UR3 not configured in RLBench: {launch_err}")
                print("    --> Fix steps:")
                print("         1. Add UR3 entry to rlbench/environment.py SUPPORTED_ROBOTS")
                print("         2. Place ur3.ttm in rlbench/robot_ttms/")
                print("         3. Create UR3 gripper config if required")
            elif "display" in err_str or "x11" in err_str or "glx" in err_str:
                fail("Environment init",
                     "No display / OpenGL context available")
                print("    --> Fix: Use Xvfb for headless rendering:")
                print("         Xvfb :99 -screen 0 1024x768x24 &")
                print("         export DISPLAY=:99")
            else:
                fail("Environment init", str(launch_err))
                print(f"    --> Raw error: {launch_err}")

    except ImportError as e:
        fail("Environment init", f"import error: {e}")
        print("    --> Hint: Ensure rlbench action_modes API matches your version.")
    except Exception as e:
        fail("Environment init", f"unexpected error during setup: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Test 6 — Summary
# ──────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SUMMARY")
print("="*60)

# Ordered list of all expected test keys
all_tests = [
    "import pyrep",
    "import rlbench",
    "import UR3 class",
    "SUPPORTED_ROBOTS check",
    "UR3 in SUPPORTED_ROBOTS",
    "ur3.ttm exists",
    "Environment init",
]

pass_count = 0
fail_count = 0
skip_count = 0

for t in all_tests:
    if t in results:
        if results[t]:
            status = "PASS"
            mark = "✓"
            pass_count += 1
        else:
            status = "FAIL"
            mark = "✗"
            fail_count += 1
    else:
        status = "SKIP"
        mark = "-"
        skip_count += 1
    print(f"  {mark} {status:4s}  {t}")

print("-"*60)
print(f"  Total: {pass_count} passed, {fail_count} failed, {skip_count} skipped")
print("="*60)

if fail_count == 0 and pass_count > 0:
    print("\n  All tests passed — UR3 environment appears ready.")
elif pass_count == 0:
    print("\n  No tests passed — check that pyrep and rlbench are installed.")
else:
    print("\n  Some tests failed — see hints above to resolve issues.")

print()
sys.exit(0 if fail_count == 0 else 1)
