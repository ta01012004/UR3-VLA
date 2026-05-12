# Hướng dẫn setup môi trường UR3 trên HPC

File này mô tả cách chuẩn bị môi trường để làm việc với UR3/UR3e trên HPC. Mục tiêu là phục vụ project VLA/robotics: mô phỏng, train/inference policy, và chuẩn bị bridge sang robot thật qua ROS/URScript/RTDE.

## 1. Kiến trúc khuyến nghị

Không nên chạy toàn bộ stack điều khiển robot thật trực tiếp trên HPC nếu HPC không cùng mạng với robot. Kiến trúc an toàn hơn:

```text
Camera + UR3 thật
   ↓
Máy gần robot: ROS2 / URScript / RTDE / gripper driver
   ↓ network
HPC/GPU: VLA inference hoặc training
   ↓ action / waypoint / command
Máy gần robot gửi lệnh an toàn về UR3
```

HPC phù hợp cho:

- train/fine-tune VLA;
- chạy inference server nếu cần GPU;
- mô phỏng RLBench/Gazebo/Isaac/MuJoCo;
- benchmark và tạo video/log.

Máy gần robot phù hợp cho:

- kết nối IP trực tiếp tới UR3;
- chạy ROS2 driver/RTDE;
- đảm bảo safety, emergency stop, workspace limit;
- nhận action từ HPC rồi convert thành lệnh robot.

## 2. Kiểm tra HPC

```bash
sinfo -o "%P %a %l %D %G"
squeue -u "$USER" -o "%i %P %t %M %D %R %b"
```

Xin node GPU interactive nếu cần:

```bash
salloc -p gpu --account=ddt_acc23 --gres=gpu:1 --cpus-per-task=4 --mem=16G --time=02:00:00
```

Sau khi được cấp node:

```bash
squeue -u "$USER" -o "%i %P %t %M %D %R %b"
ssh <node_duoc_cap>
nvidia-smi
```

## 3. Môi trường Python cơ bản

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda create -n ur3-hpc python=3.10 -y
conda activate ur3-hpc
python -m pip install --upgrade pip setuptools wheel
```

Gói Python hay dùng:

```bash
pip install numpy scipy opencv-python pillow imageio matplotlib pyyaml tqdm
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

Nếu chỉ chạy CPU:

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

## 4. Cài ROS2/UR driver

ROS2 thường nên cài bằng system package hoặc container. Nếu HPC không có quyền `sudo`, dùng Apptainer/Singularity hoặc build trên máy gần robot.

### Cách A: máy có sẵn ROS2

Kiểm tra:

```bash
source /opt/ros/humble/setup.bash
ros2 --version
```

Tạo workspace:

```bash
mkdir -p ~/ur_ws/src
cd ~/ur_ws/src
git clone https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver.git
git clone https://github.com/UniversalRobots/Universal_Robots_ROS2_Description.git
cd ~/ur_ws
rosdep update
rosdep install --ignore-src --from-paths src -y
colcon build
source install/setup.bash
```

### Cách B: HPC không có ROS2 hoặc không có sudo

Dùng Apptainer với image ROS2 Humble đã cài sẵn dependency cho Universal Robots driver.
Không nên dùng trực tiếp `docker://osrf/ros:humble-desktop` để build `ur_ws`, vì image gốc thường thiếu `ros2_control` và sẽ lỗi kiểu:

```text
Could not find a package configuration file provided by "controller_interface"
```

#### B1. Build image Apptainer mới

Repo có sẵn definition file:

```text
containers/ros_humble_ur.def
```

Trên HPC:

```bash
mkdir -p ~/containers
cd ~/containers

# Nếu đang ở thư mục repo UR3-VLA, có thể copy file def từ repo:
cp /path/to/UR3-VLA/containers/ros_humble_ur.def ./ros_humble_ur.def

apptainer build --fakeroot ros_humble_ur.sif ros_humble_ur.def
```

Nếu HPC không cho `--fakeroot`, thử build sandbox writable:

```bash
apptainer build --sandbox --fakeroot ros_humble_ur_sandbox ros_humble_ur.def
apptainer build ros_humble_ur.sif ros_humble_ur_sandbox
```

Nếu cả hai cách đều bị chặn, cần nhờ admin build image hoặc build ở máy khác rồi upload `ros_humble_ur.sif` lên HPC.

#### B2. Vào container mới

```bash
apptainer shell --nv \
  --bind /home/$USER:/home/$USER \
  ~/containers/ros_humble_ur.sif
```

Trong container:

```bash
source /opt/ros/humble/setup.bash
ros2 pkg prefix controller_interface
```

Nếu lệnh trên in ra `/opt/ros/humble`, dependency `controller_interface` đã có.

#### B3. Clone và build UR workspace

```bash
source /opt/ros/humble/setup.bash
mkdir -p ~/ur_ws/src
cd ~/ur_ws/src

git clone https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver.git
git clone https://github.com/UniversalRobots/Universal_Robots_ROS2_Description.git

cd ~/ur_ws
rosdep update
rosdep install --ignore-src --from-paths src -y -r

colcon build
source install/setup.bash
```

#### B4. Nếu vẫn lỗi thiếu package

Kiểm tra package thiếu, ví dụ:

```bash
ros2 pkg prefix controller_interface
ros2 pkg prefix control_msgs
ros2 pkg prefix controller_manager
```

Nếu package nào không có, thêm package apt tương ứng vào `containers/ros_humble_ur.def`, build lại image, rồi clean build workspace:

```bash
cd ~/ur_ws
rm -rf build install log
colcon build
```

## 5. Setup UR3 thật

Trên teach pendant của UR3:

1. Cài External Control URCap.
2. Cấu hình IP robot và IP máy điều khiển.
3. Tạo program có node External Control.
4. Bấm Play để robot chờ lệnh ngoài.

Trên máy điều khiển ROS2:

```bash
source /opt/ros/humble/setup.bash
source ~/ur_ws/install/setup.bash
ros2 launch ur_robot_driver ur_control.launch.py \
  ur_type:=ur3 \
  robot_ip:=<IP_UR3> \
  launch_rviz:=false
```

Với UR3e, đổi:

```bash
ur_type:=ur3e
```

## 6. Điều khiển bằng ROS2/MoveIt

Nếu dùng MoveIt:

```bash
ros2 launch ur_moveit_config ur_moveit.launch.py \
  ur_type:=ur3 \
  launch_rviz:=true
```

Các action từ VLA nên được convert thành:

- target pose;
- delta end-effector pose;
- joint trajectory;
- gripper open/close;
- high-level primitive như `pick`, `place`, `push`.

Không nên để VLA gửi lệnh motor thô trực tiếp vào robot thật.

## 7. Điều khiển bằng URScript/RTDE

Nếu không dùng ROS2, có thể dùng URScript/RTDE từ Python.

Ví dụ cài thư viện Python:

```bash
conda activate ur3-hpc
pip install ur-rtde
```

Pseudo-code:

```python
import rtde_control
import rtde_receive

robot_ip = "192.168.0.10"
rtde_c = rtde_control.RTDEControlInterface(robot_ip)
rtde_r = rtde_receive.RTDEReceiveInterface(robot_ip)

pose = rtde_r.getActualTCPPose()
target = pose[:]
target[0] += 0.02
rtde_c.moveL(target, 0.05, 0.1)
rtde_c.stopScript()
```

Luôn test với tốc độ thấp, workspace nhỏ, và có người đứng gần nút dừng khẩn cấp.

## 8. Môi trường VLA trên HPC

Tạo env riêng cho VLA:

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda create -n vla-hpc python=3.10 -y
conda activate vla-hpc
python -m pip install --upgrade pip setuptools wheel
pip install torch torchvision transformers accelerate peft pillow opencv-python
```

Hướng triển khai:

```text
HPC chạy VLA server
Máy gần UR3 chạy ROS2/RTDE client
Client gửi ảnh + instruction lên HPC
HPC trả action
Client kiểm tra safety rồi gửi lệnh vào UR3
```

Ví dụ server API đơn giản:

```text
POST /act
input: image, instruction, robot_state
output: action
```

Action nên là dạng an toàn:

```text
{
  "type": "delta_pose",
  "dx": 0.01,
  "dy": 0.00,
  "dz": 0.00,
  "gripper": "open"
}
```

## 9. Mô phỏng trước khi chạy robot thật

Với project này đã có RLBench/CoppeliaSim:

```bash
cd "/home/22011107/TA/Capstone 2/rlbench_hpc_smoke_test"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate rlbench-hpc
RLBENCH_TASK=slide_block_to_target sbatch slurm_run_video.sh
```

Kết quả video:

```bash
outputs/<JOBID>_slide_block_to_target/simulation.mp4
```

Lưu ý: RLBench upstream có `ur5`, nhưng chưa có sẵn `ur3`. Với UR3 cần tích hợp robot model/config riêng trước khi benchmark đúng embodiment.

## 10. Checklist tối thiểu

Trước khi chạy thật:

- UR3 đã cài External Control URCap.
- Máy điều khiển ping được IP robot.
- ROS2 driver hoặc RTDE chạy ổn.
- Camera calibration đã có.
- Có workspace limit và speed limit.
- Có nút dừng khẩn cấp.
- VLA chỉ sinh action cấp cao hoặc delta pose nhỏ.
- Có lớp safety check trước khi gửi lệnh robot.

Nguồn tham khảo chính:

- Universal Robots ROS2 driver: https://github.com/UniversalRobots/Universal_Robots_ROS2_Driver
- Universal Robots ROS2 description: https://github.com/UniversalRobots/Universal_Robots_ROS2_Description
- UR ROS2 documentation: https://docs.universal-robots.com/Universal_Robots_ROS2_Documentation/
- RTDE Python client: https://sdurobotics.gitlab.io/ur_rtde/
