# RLBench HPC smoke test: headless frames -> video

Mục tiêu: cài RLBench trên HPC, chạy CoppeliaSim/PyRep ở `headless=True`, lấy observation từng step từ một live demo có object (`PickUpCup`), lưu frame PNG và ghép thành `simulation.mp4`.

## Files

- `requirements.txt`: Python dependencies cơ bản.
- `install_hpc.sh`: tải CoppeliaSim 4.1.0, export env vars, cài PyRep/RLBench bằng commit pin.
- `run_rlbench_video.py`: chạy RLBench headless, lưu frame + mp4 + metadata.
- `slurm_run_video.sh`: mẫu job SLURM có check conda, CoppeliaSim, `DISPLAY`/`xvfb-run`.
- `outputs/`: nơi lưu kết quả.

## Quick run on HPC

```bash
cd rlbench_hpc_smoke_test
conda create -n rlbench-hpc python=3.8 -y
conda activate rlbench-hpc
bash install_hpc.sh

# Nếu HPC có GPU DISPLAY sẵn:
python run_rlbench_video.py --out outputs/test_pick_up_cup

# Nếu không có DISPLAY, thử Xvfb:
xvfb-run -a -s "-screen 0 1280x1024x24" python run_rlbench_video.py --out outputs/test_pick_up_cup
```

Hoặc submit SLURM:

```bash
sbatch slurm_run_video.sh
```

Nếu tên env khác:

```bash
CONDA_ENV_NAME=my-env sbatch slurm_run_video.sh
```

Kết quả mong đợi:

```text
outputs/test_pick_up_cup/
  frames/frame_00000.png
  frames/frame_00001.png
  ...
  simulation.mp4
  metadata.json
```

## HPC readiness checklist

Trước khi chạy job, kiểm tra:

```bash
python --version        # nên là Python 3.8.x
which python
python -c "import rlbench, pyrep; print('ok')"
test -f "$COPPELIASIM_ROOT/coppeliaSim.sh" && echo ok
command -v xvfb-run || echo "xvfb-run missing; need DISPLAY/GPU X server"
```

## Notes for headless HPC

RLBench dùng CoppeliaSim/PyRep. Dù đặt `headless=True`, rendering camera vẫn cần OpenGL context. Trên cluster thường cần một trong các cách sau:

1. GPU node đã có `DISPLAY`/VirtualGL/EGL cấu hình bởi admin.
2. X server headless như `X :99` theo hướng dẫn RLBench.
3. `xvfb-run` cho smoke test đơn giản, nhưng có thể chậm/lỗi OpenGL trên một số HPC.

Nếu lỗi kiểu Qt/XCB/OpenGL, cần module/package hệ thống tương ứng: X11/XCB, libGL/Mesa hoặc NVIDIA GL, `libxkbcommon-x11`, và Xvfb/VirtualGL tuỳ cluster.

## Robot UR3/UR5 note

Upstream RLBench hỗ trợ đổi arm qua `robot_setup`, nhưng danh sách chính thức có `ur5`, chưa có sẵn `ur3`. Script có flag:

```bash
python run_rlbench_video.py --robot-setup ur5
```

Với UR3, hướng khả thi là import model UR3 vào PyRep/CoppeliaSim rồi tích hợp robot configuration vào RLBench. Việc này không chỉ là đổi file URDF; cần mapping joints, gripper, tip/dummy objects, planning/IK và task workspace. Vì vậy bước đầu nên chạy smoke test bằng `panda` hoặc `ur5`, sau đó mới thử port UR3.

## Current assessment

Sau review, folder này **có thể upload lên HPC để test**, nhưng khả năng chạy phụ thuộc chủ yếu vào cluster có một trong hai thứ:

- `DISPLAY`/GPU-backed X server/VirtualGL đã được admin cấu hình; hoặc
- `xvfb-run` + OpenGL software rendering hoạt động đủ cho CoppeliaSim.

Nếu cả hai không có, RLBench vẫn cài được nhưng phần render camera để lưu frame/video sẽ lỗi.

## Sources checked

- RLBench README: built around CoppeliaSim v4.1.0 + PyRep; install and headless rendering notes.
- PyRep docs/README: `launch(..., headless=True)` and CoppeliaSim environment variables.
