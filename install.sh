#!/bin/bash

# Get the directory where the installer script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Default to standard PX4-Autopilot directory in home if no arguments passed
PX4_DIR="${1:-$HOME/PX4-Autopilot}"
CUSTOM_TARGET="4041_gz_x500_custom"
AIRFRAME_SOURCE="$SCRIPT_DIR/airframes/${CUSTOM_TARGET}"
MODEL_SOURCE="$SCRIPT_DIR/models/x500_custom"

echo "========================================="
echo " Installing PX4 Custom x500 Environment  "
echo "========================================="
echo "Target PX4 Directory: $PX4_DIR"

if [ ! -d "$PX4_DIR" ]; then
    echo "ERROR: PX4 directory not found at '$PX4_DIR'!"
    echo "Usage: ./install.sh /path/to/PX4-Autopilot"
    exit 1
fi

# 1. Copy the Gazebo model into PX4's internal tools directory
DEST_MODELS="$PX4_DIR/Tools/simulation/gz/models"
echo "-> Copying custom gazebo model to: $DEST_MODELS"
mkdir -p "$DEST_MODELS"
cp -r "$MODEL_SOURCE" "$DEST_MODELS/"

# 2. Copy the Airframe configuration
DEST_AIRFRAMES="$PX4_DIR/ROMFS/px4fmu_common/init.d-posix/airframes"
echo "-> Copying custom airframe to: $DEST_AIRFRAMES"
mkdir -p "$DEST_AIRFRAMES"
cp "$AIRFRAME_SOURCE" "$DEST_AIRFRAMES/"

# 3. Patch the CMakeLists.txt to register the airframe if it's missing
CMAKE_FILE="$DEST_AIRFRAMES/CMakeLists.txt"
if [ ! -f "$CMAKE_FILE" ]; then
    echo "ERROR: Could not find CMakeLists.txt at '$CMAKE_FILE'."
    exit 1
fi

echo "-> Checking CMakeLists.txt for $CUSTOM_TARGET registration..."
if grep -q "$CUSTOM_TARGET" "$CMAKE_FILE"; then
    echo "   Target already registered in CMakeLists.txt. Skipping patch."
else
    echo "   Registering '$CUSTOM_TARGET' in CMakeLists.txt..."
    # Using awk to safely insert the custom airframe target at the bottom of the list
    awk -v target="\t${CUSTOM_TARGET}" '
    /^[[:space:]]*#[[:space:]]*\[22000, 22999\] Reserve for custom models/ {
        print target
        print ""
        print $0
        next
    }
    {print}
    ' "$CMAKE_FILE" > tmp_cmake && mv tmp_cmake "$CMAKE_FILE"
fi

# 4. Clean Cache
echo "-> Clearing PX4 SITL build cache to force CMake to recognize new airframes..."
rm -rf "$PX4_DIR/build/px4_sitl_default"

echo "========================================="
echo "                SUCCESS!                 "
echo "========================================="
echo "The custom x500 environment has been injected into your PX4 repository."
echo ""
echo "To test the drone in simulation, run:"
echo "  cd $PX4_DIR"
echo "  make px4_sitl gz_x500_custom"
echo ""
