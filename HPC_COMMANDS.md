# Tổng hợp lệnh chạy RLBench trên HPC

File này ghi các lệnh hay dùng để vào HPC, kiểm tra GPU, submit job RLBench/PyRep/CoppeliaSim, theo dõi log và lấy kết quả video.

Job smoke test gần nhất:

```text
JOBID: 71507
Trạng thái: COMPLETED
Kết quả: outputs/71507_pick_up_cup/simulation.mp4
```

Khi submit job mới, thay `71507` bằng job id mới nhất.

## 1. Vào thư mục project

```bash
cd "/home/22011107/TA/Capstone 2/rlbench_hpc_smoke_test"
```

## 2. Kiểm tra queue và GPU

Xem job của mình:

```bash
squeue -u "$USER" -o "%i %P %t %M %D %R %b"
```

Xem queue GPU:

```bash
squeue -p gpu,dgx-tiny,dgx-small,dgx-large,dgx-long,dgx-full -o "%i %u %P %t %M %D %R %b"
```

Xem partition:

```bash
sinfo -o "%P %a %l %D %G"
```

Xem từng node GPU:

```bash
sinfo -N -o "%N %P %t %G %C %m" | egrep "gpu|dgx|NODELIST"
```

Xem chi tiết node:

```bash
scontrol show node hpc22
scontrol show node hpc23
scontrol show node hpc24
scontrol show node hpc-dgx01
```

Cách đọc GPU còn trống:

```text
CfgTRES=... gres/gpu=1
AllocTRES=... gres/gpu=1
```

Nếu node chỉ có `gres/gpu=1` và `AllocTRES` cũng có `gres/gpu=1`, GPU đó đã bị dùng.

## 3. Cách vào compute node bằng salloc và ssh

Không SSH thẳng vào node nếu chưa có allocation. Cluster có `pam_slurm_adopt`, nên SSH vào compute node chỉ được phép sau khi SLURM đã cấp node cho mình.

Xin GPU interactive:

```bash
salloc -p gpu --account=ddt_acc23 --gres=gpu:1 --cpus-per-task=4 --mem=8G --time=00:30:00
```

Khi `salloc` cấp node thành công, xem node được cấp:

```bash
squeue -u "$USER" -o "%i %P %t %M %D %R %b"
```

Ví dụ nếu thấy node là `hpc22`, SSH vào node:

```bash
ssh hpc22
```

Vào node xong kiểm tra:

```bash
hostname
nvidia-smi
```

Nếu muốn thử xin node nhưng không muốn chờ lâu:

```bash
salloc -p gpu --account=ddt_acc23 --gres=gpu:1 --cpus-per-task=4 --mem=8G --time=00:30:00 --immediate=60
```

Nếu báo busy hoặc timeout, nghĩa là chưa có GPU trống ngay.

## 4. Kích hoạt môi trường

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rlbench-hpc
```

Nếu chưa có môi trường:

```bash
conda create -n rlbench-hpc python=3.8 -y
conda activate rlbench-hpc
```

## 5. Cài hoặc cập nhật môi trường

Chạy sau khi activate `rlbench-hpc`:

```bash
bash install_hpc.sh
```

Script này sẽ cài Python dependencies, PyRep, RLBench và CoppeliaSim 4.1.0.

Cài thêm Xvfb vào conda env để chạy render trên node không có `DISPLAY`:

```bash
conda install -y xorg-xserver-xvfb
```

Trên môi trường glibc `2.28`, dùng bản CoppeliaSim:

```text
CoppeliaSim_Edu_V4_1_0_Ubuntu18_04
```

## 6. Export biến CoppeliaSim khi chạy thủ công

```bash
export COPPELIASIM_ROOT="$PWD/third_party/CoppeliaSim_Edu_V4_1_0_Ubuntu18_04"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:$COPPELIASIM_ROOT"
export QT_QPA_PLATFORM_PLUGIN_PATH="$COPPELIASIM_ROOT"
```

Kiểm tra import:

```bash
python - <<'PY'
import sys, rlbench, pyrep
print("[check] Python:", sys.version)
print("[check] RLBench:", rlbench.__file__)
print("[check] PyRep:", pyrep.__file__)
PY
```

## 7. Submit job batch thông thường

Submit bằng script có sẵn:

```bash
sbatch slurm_run_video.sh
```

Submit rõ partition/account:

```bash
sbatch --partition=gpu --account=ddt_acc23 --gres=gpu:1 slurm_run_video.sh
```

Submit vào node cụ thể:

```bash
sbatch --partition=gpu --account=ddt_acc23 --gres=gpu:1 --nodelist=hpc22 slurm_run_video.sh
```

Dry run để xem SLURM có nhận cấu hình không:

```bash
sbatch --test-only --partition=gpu --account=ddt_acc23 --gres=gpu:1 slurm_run_video.sh
```

## 8. Theo dõi job batch

Xem job gần nhất:

```bash
squeue -j 71507 -o "%i %P %t %M %D %R %b"
```

Xem chi tiết:

```bash
scontrol show job 71507
```

Xem thời gian dự kiến bắt đầu:

```bash
squeue --start -j 71507
```

Huỷ job:

```bash
scancel 71507
```

## 9. Đọc log

Với job `71507`:

```bash
tail -f rlbench-video-71507.out
tail -f rlbench-video-71507.err
```

Nếu submit job mới, thay `71507` bằng job id mới.

## 10. Xem kết quả video

Kết quả nằm trong:

```bash
outputs/<JOBID>_pick_up_cup/
```

Ví dụ:

```bash
ls -R outputs/71507_pick_up_cup
```

Kết quả mong đợi:

```text
frames/frame_00000.png
frames/frame_00001.png
...
simulation.mp4
metadata.json
```

File video chính:

```text
outputs/<JOBID>_pick_up_cup/simulation.mp4
```

## 11. Chạy thủ công sau khi đã vào node

Nếu node có `DISPLAY`:

```bash
python run_rlbench_video.py --out outputs/manual_pick_up_cup --camera front_rgb --fps 20
```

Nếu node có `xvfb-run`:

```bash
xvfb-run -a -s "-screen 0 1280x1024x24" \
  python run_rlbench_video.py --out outputs/manual_pick_up_cup --camera front_rgb --fps 20
```

Nếu không có `DISPLAY` và không có `xvfb-run`, `slurm_run_video.sh` sẽ tự bật `Xvfb` từ conda env nếu đã cài `xorg-xserver-xvfb`.

## 12. Ghi chú quan trọng

- Không SSH thẳng vào `hpc22`, `hpc23`, `hpc24` nếu chưa có allocation/job đang chạy trên node đó.
- Cách vào node đúng là xin bằng `salloc`, sau đó SSH vào node được cấp.
- Nếu chỉ cần chạy smoke test lấy video, dùng `sbatch slurm_run_video.sh` là cách ổn định hơn.
- Login/session hiện tại không có `DISPLAY` và không có `xvfb-run`, nên cần dùng `Xvfb` trong conda env hoặc node được cấu hình X/VirtualGL.
- CoppeliaSim Ubuntu 20.04 yêu cầu `GLIBC_2.29`; môi trường glibc `2.28` cần dùng bản Ubuntu 18.04.
