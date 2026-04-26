# Huong dan cai dat va chay CoppeliaSim/RLBench tren HPC

File nay tap trung rieng vao phan CoppeliaSim/RLBench: cach cai moi truong, cach chay task sinh video, cach doc ket qua, va giai thich policy dang dung trong video hien tai.

## 1. Muc tieu

Pipeline hien tai dung de kiem tra:

- HPC co chay duoc RLBench/PyRep/CoppeliaSim khong;
- CoppeliaSim co render duoc tren node khong co man hinh khong;
- task RLBench co sinh duoc demo va video `simulation.mp4` khong.

Video hien tai chua phai VLA policy. Video duoc tao tu ban trinh dien chuyen gia cua RLBench trong mo phong.

## 2. Vao thu muc project

```bash
cd "/home/22011107/TA/Capstone 2/rlbench_hpc_smoke_test"
```

## 3. Tao va kich hoat moi truong

Dung Python 3.8 vi PyRep/RLBench ban cu on dinh nhat voi Python 3.8.

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda create -n rlbench-hpc python=3.8 -y
conda activate rlbench-hpc
```

Neu moi truong da ton tai:

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rlbench-hpc
```

## 4. Cai RLBench, PyRep va CoppeliaSim

Chay script cai dat:

```bash
bash install_hpc.sh
```

Script nay se:

- cai Python packages trong `requirements.txt`;
- tai CoppeliaSim 4.1.0 vao `third_party/`;
- chon ban CoppeliaSim theo glibc cua may;
- cai PyRep tu GitHub;
- cai RLBench tu GitHub;
- cai `xorg-xserver-xvfb` trong conda env neu co conda.

Tren HPC hien tai, glibc la `2.28`, nen can dung:

```text
CoppeliaSim_Edu_V4_1_0_Ubuntu18_04
```

Khong nen dung ban Ubuntu 20.04 neu may bao loi kieu:

```text
GLIBC_2.29 not found
```

## 5. Export bien CoppeliaSim khi chay thu cong

Neu chay thu cong, export cac bien sau:

```bash
export COPPELIASIM_ROOT="$PWD/third_party/CoppeliaSim_Edu_V4_1_0_Ubuntu18_04"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:$COPPELIASIM_ROOT"
export QT_QPA_PLATFORM_PLUGIN_PATH="$COPPELIASIM_ROOT"
```

Kiem tra import:

```bash
python - <<'PY'
import sys, rlbench, pyrep
print("[check] Python:", sys.version)
print("[check] RLBench:", rlbench.__file__)
print("[check] PyRep:", pyrep.__file__)
PY
```

## 6. Chay bang SLURM batch

Cach on dinh nhat la submit job:

```bash
sbatch slurm_run_video.sh
```

Neu can ghi ro partition/account:

```bash
sbatch --partition=gpu --account=ddt_acc23 --gres=gpu:1 slurm_run_video.sh
```

Script `slurm_run_video.sh` se tu:

- activate env `rlbench-hpc` neu can;
- thiet lap `COPPELIASIM_ROOT`;
- bat `Xvfb` neu node khong co `DISPLAY`;
- chay `run_rlbench_video.py`;
- luu video va metadata vao `outputs/`.

## 7. Chay task cu the

Mac dinh script chay:

```text
pick_up_cup
```

Muon chay task day vat vao vi tri dich:

```bash
RLBENCH_TASK=slide_block_to_target sbatch slurm_run_video.sh
```

Muon chay task khac, doi bien `RLBENCH_TASK` thanh ten module task cua RLBench:

```bash
RLBENCH_TASK=<ten_task> sbatch slurm_run_video.sh
```

Vi du:

```bash
RLBENCH_TASK=reach_target sbatch slurm_run_video.sh
RLBENCH_TASK=open_drawer sbatch slurm_run_video.sh
```

## 8. Theo doi job

Sau khi submit, SLURM tra ve job id. Vi du:

```text
Submitted batch job 71514
```

Kiem tra job:

```bash
squeue -j 71514 -o "%i %P %t %M %D %R %b"
```

Xem log:

```bash
tail -f rlbench-video-71514.out
tail -f rlbench-video-71514.err
```

Neu can huy job:

```bash
scancel 71514
```

## 9. Xem ket qua

Ket qua nam trong:

```text
outputs/<JOBID>_<TASK>/
```

Vi du:

```text
outputs/71507_pick_up_cup/
outputs/71514_slide_block_to_target/
```

Trong moi thu muc ket qua se co:

```text
frames/
simulation.mp4
metadata.json
```

Y nghia:

- `frames/`: tung anh RGB lay tu camera cua RLBench;
- `simulation.mp4`: video duoc ghep tu cac frame;
- `metadata.json`: task, mo ta ngon ngu, robot setup, camera, joint positions, trang thai gripper.

## 10. Chay thu cong sau khi da vao node

Neu node co `DISPLAY`:

```bash
python run_rlbench_video.py \
  --out outputs/manual_pick_up_cup \
  --task pick_up_cup \
  --camera front_rgb \
  --fps 20
```

Neu khong co `DISPLAY` nhung co `xvfb-run`:

```bash
xvfb-run -a -s "-screen 0 1280x1024x24" \
  python run_rlbench_video.py \
    --out outputs/manual_pick_up_cup \
    --task pick_up_cup \
    --camera front_rgb \
    --fps 20
```

Neu khong co `DISPLAY` va khong co `xvfb-run`, nen dung `sbatch slurm_run_video.sh` vi script da co fallback tu bat `Xvfb`.

## 11. Policy trong video la gi?

Policy trong video hien tai khong phai model VLA, khong phai OpenVLA, va cung khong phai policy hoc may tu train.

Code dang goi:

```python
demos = task.get_demos(1, live_demos=True)
```

Dong nay yeu cau RLBench sinh mot ban trinh dien chuyen gia truc tiep trong CoppeliaSim.

Co the hieu nhu sau:

```text
CoppeliaSim: trinh mo phong robot, vat the, camera, vat ly
RLBench: bo task nam tren CoppeliaSim
Task oracle/scripted expert: kich ban/waypoint co san de robot lam dung nhiem vu
run_rlbench_video.py: ghi lai anh tung buoc va ghep thanh video
```

Vi vay, video hien tai la:

```text
RLBench tao task va vi tri vat the
RLBench dung kich ban/waypoint co san de sinh trajectory mau
Robot Panda trong CoppeliaSim di theo trajectory do
Script luu frame va ghep thanh simulation.mp4
```

No nen duoc goi la:

```text
ban trinh dien chuyen gia cua RLBench
```

Khong nen goi la:

```text
VLA policy
policy train san
policy co san trong CoppeliaSim
```

Noi chinh xac hon:

> Robot trong CoppeliaSim dang thuc hien mot ban trinh dien chuyen gia do RLBench sinh ra tu kich ban/waypoint co san cua task, chua phai policy hoc may hay VLA.

## 12. Vi sao ban trinh dien nay huu ich?

Ban trinh dien chuyen gia co the dung de:

- kiem tra cai dat RLBench/CoppeliaSim;
- tao video minh hoa task;
- tao du lieu mau gom anh, joint state, gripper state;
- lam nguon du lieu ban dau cho imitation learning;
- so sanh voi policy hoc may sau nay.

Nhung no khong the be thang sang UR3 that, vi no phu thuoc vao:

- scene trong CoppeliaSim;
- waypoint cua task RLBench;
- robot setup trong mo phong;
- thong tin noi bo cua simulator.

## 13. Robot dang dung trong video

Mac dinh hien tai:

```text
robot_setup = panda
```

Nghia la video dang dung robot Franka Panda trong RLBench, khong phai UR3 that.

RLBench upstream co mot so robot setup nhu:

```text
panda, ur5, sawyer, mico, jaco
```

Hien chua co setup UR3 san trong pipeline nay. Muon benchmark dung UR3 thi can tich hop model/config UR3 rieng.

## 14. Cau lenh nhanh hay dung

Chay task nhat coc:

```bash
cd "/home/22011107/TA/Capstone 2/rlbench_hpc_smoke_test"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rlbench-hpc
RLBENCH_TASK=pick_up_cup sbatch slurm_run_video.sh
```

Chay task day block vao target:

```bash
cd "/home/22011107/TA/Capstone 2/rlbench_hpc_smoke_test"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rlbench-hpc
RLBENCH_TASK=slide_block_to_target sbatch slurm_run_video.sh
```

Xem output sau khi chay xong:

```bash
ls -R outputs/<JOBID>_<TASK>
```

Video chinh:

```text
outputs/<JOBID>_<TASK>/simulation.mp4
```
