# UR3-VLA

Repo này lưu hướng dẫn và script phục vụ thử nghiệm UR3/VLA trên HPC, trước mắt tập trung vào pipeline mô phỏng RLBench/CoppeliaSim để tạo video smoke test.

## Nội dung chính

- `HPC_COMMANDS.md`: tổng hợp lệnh vào HPC, kiểm tra GPU, submit job, đọc log và lấy kết quả.
- `UR3_HPC_SETUP.md`: hướng dẫn setup môi trường UR3/ROS2/RTDE/VLA trên HPC hoặc máy gần robot.
- `COPPELIASIM_RLBENCH_SETUP.md`: hướng dẫn riêng cho CoppeliaSim/RLBench, gồm cài đặt, chạy task, xem video và giải thích demo chuyên gia.
- `rlbench_hpc_smoke_test/`: script chạy RLBench headless để sinh video.

## Chạy nhanh RLBench/CoppeliaSim trên HPC

Vào thư mục smoke test:

```bash
cd rlbench_hpc_smoke_test
```

Tạo môi trường:

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda create -n rlbench-hpc python=3.8 -y
conda activate rlbench-hpc
```

Cài dependencies, PyRep, RLBench và CoppeliaSim:

```bash
bash install_hpc.sh
```

Submit job mặc định `pick_up_cup`:

```bash
sbatch slurm_run_video.sh
```

Submit task đẩy vật vào vị trí đích:

```bash
RLBENCH_TASK=slide_block_to_target sbatch slurm_run_video.sh
```

Kết quả nằm trong:

```text
rlbench_hpc_smoke_test/outputs/<JOBID>_<TASK>/simulation.mp4
```

Ví dụ:

```text
outputs/71507_pick_up_cup/simulation.mp4
outputs/71514_slide_block_to_target/simulation.mp4
```

## Policy trong video hiện tại

Video hiện tại chưa dùng VLA hoặc policy học máy. Script gọi:

```python
demos = task.get_demos(1, live_demos=True)
```

Điều này yêu cầu RLBench sinh **bản trình diễn chuyên gia** trong CoppeliaSim. Robot trong video đang đi theo trajectory mẫu do RLBench tạo từ kịch bản/waypoint có sẵn của task.

Nói ngắn gọn:

```text
CoppeliaSim dựng môi trường
RLBench tạo task và demo chuyên gia
run_rlbench_video.py ghi frame
imageio ghép frame thành simulation.mp4
```

## Ghi chú quan trọng

- Robot mặc định trong smoke test là `panda`, chưa phải UR3 thật.
- RLBench upstream có `ur5`, nhưng chưa có setup UR3 sẵn trong pipeline này.
- CoppeliaSim binary và output video không nên commit lên GitHub vì nặng; `install_hpc.sh` sẽ tải CoppeliaSim khi chạy.
- Trên HPC glibc `2.28`, dùng CoppeliaSim `Ubuntu18_04` để tránh lỗi `GLIBC_2.29 not found`.

## Tài liệu nên đọc

1. `COPPELIASIM_RLBENCH_SETUP.md` nếu muốn chạy video mô phỏng.
2. `HPC_COMMANDS.md` nếu muốn submit job và kiểm tra GPU.
3. `UR3_HPC_SETUP.md` nếu muốn nối hướng mô phỏng sang UR3/ROS2/RTDE/VLA.
