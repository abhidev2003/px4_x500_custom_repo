# PX4 x500 Custom SITL Setup

This repository contains the physical model files and configurations for our custom PX4 `x500` drone, complete with downward optical flow, a forward camera, and sensors. 

Because PX4's build system does not easily permit loading custom drone models from external directories without aggressively triggering CMake errors, this repository includes an installer script that securely copies our custom drone into your local PX4 repository.

## Installation

You must already have [PX4-Autopilot](https://github.com/PX4/PX4-Autopilot) cloned on your PC to continue.

1. **Clone this repository** anywhere on your PC:
   ```bash
   git clone <URL_TO_THIS_REPO>
   cd px4_x500_custom_repo
   ```

2. **Run the installer script** and pass the path to your PX4 installation directory. If your PX4 folder is located at `~/PX4-Autopilot`, you don't need to specify the path.
   ```bash
   ./install.sh /path/to/your/PX4-Autopilot
   ```

3. **Launch the Drone** using the standard PX4 Make targets:
   ```bash
   cd ~/PX4-Autopilot
   make px4_sitl gz_x500_custom
   ```

## What the script does:
The `install.sh` script automates the tedious boilerplate required to bypass PX4 path hardcoding:
* Copies the Gazebo simulated model (`models/x500_custom`) into `PX4-Autopilot/Tools/simulation/gz/models`.
* Copies the PX4 startup configuration (`4041_gz_x500_custom`) into `PX4-Autopilot/ROMFS/px4fmu_common/init.d-posix/airframes`.
* Modifies `ROMFS/px4fmu_common/init.d-posix/airframes/CMakeLists.txt` to inject our custom airframe into the build process if it isn't listed already.
* Cleans the build cache so the next `make` triggers a full file inclusion correctly.
