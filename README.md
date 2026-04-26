# UR3-VLA

Repo này lưu script và hướng dẫn phục vụ thử nghiệm UR3/VLA trên HPC. Phần hiện tại tập trung vào pipeline mô phỏng RLBench/CoppeliaSim để tạo video smoke test trước khi chuyển sang robot thật.

## Cấu trúc repo

```text
README.md
COPPELIASIM_RLBENCH_SETUP.md
UR3_HPC_SETUP.md
rlbench_hpc_smoke_test/
  install_hpc.sh
  requirements.txt
  run_rlbench_video.py
  slurm_run_video.sh
```

## Chạy nhanh RLBench/CoppeliaSim trên HPC

```bash
cd rlbench_hpc_smoke_test
source "$(conda info --base)/etc/profile.d/conda.sh"
conda create -n rlbench-hpc python=3.8 -y
conda activate rlbench-hpc
bash install_hpc.sh
```

Chạy task mặc định `pick_up_cup`:

```bash
sbatch slurm_run_video.sh
```

Chạy task đẩy vật vào vị trí đích:

```bash
RLBENCH_TASK=slide_block_to_target sbatch slurm_run_video.sh
```

Kết quả nằm trong:

```text
rlbench_hpc_smoke_test/outputs/<JOBID>_<TASK>/simulation.mp4
```

## Policy trong video hiện tại

Video hiện tại chưa dùng VLA hoặc policy học máy. Script gọi:

```python
demos = task.get_demos(1, live_demos=True)
```

Điều này yêu cầu RLBench sinh **bản trình diễn chuyên gia** trong CoppeliaSim. Robot trong video đi theo trajectory mẫu do RLBench tạo từ kịch bản/waypoint có sẵn của task.

## Tài liệu chính

- `COPPELIASIM_RLBENCH_SETUP.md`: hướng dẫn chi tiết cài và chạy CoppeliaSim/RLBench trên HPC.
- `UR3_HPC_SETUP.md`: hướng dẫn setup UR3/ROS2/RTDE/VLA và hướng kết nối sang robot thật.

## Ghi chú

- Robot mặc định trong smoke test là `panda`, chưa phải UR3 thật.
- CoppeliaSim binary, output video, frame và log job không commit lên GitHub; script sẽ tự tạo/tải lại khi chạy.
- Trên HPC glibc `2.28`, dùng CoppeliaSim `Ubuntu18_04` để tránh lỗi `GLIBC_2.29 not found`.
