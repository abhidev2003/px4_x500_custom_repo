#!/bin/bash
# =======================================================================
# PX4 x500 Custom SITL - ROS 2 Camera Bridge
# -----------------------------------------------------------------------
# This script bridges the Gazebo simulated camera feeds into native ROS 2 
# Image topics so they can be consumed by MobileNet, YOLOv8n, or other 
# OpenCV scripts running on your simulated companion computer.
# =======================================================================

echo "Starting ROS 2 <-> Gazebo Camera Bridges..."

# 1. Bridge the Forward Pi Camera Rev 1.3 (For YOLOv8n Obstacle Avoidance)
ros2 run ros_gz_bridge parameter_bridge /world/default/model/x500_custom_0/link/pi_cam_front_link/sensor/pi_cam_front/image@sensor_msgs/msg/Image[gz.msgs.Image &
PID1=$!

# 2. Bridge the Downward USB Camera (For Precision Landing / Flow) 
ros2 run ros_gz_bridge parameter_bridge /world/default/model/x500_custom_0/link/usb_cam_down_link/sensor/usb_cam_down/image@sensor_msgs/msg/Image[gz.msgs.Image &
PID2=$!

echo "======================================================================"
echo " Bridges are active! Your simulated Pi 4 can now access the feeds."
echo " To view the feeds manually, you can run: rqt_image_view"
echo "======================================================================"

# Wait for bridges (Press Ctrl+C to terminate)
wait $PID1 $PID2
