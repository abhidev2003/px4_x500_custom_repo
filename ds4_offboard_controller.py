#!/usr/bin/env python3
"""
DualShock 4 Offboard Controller for PX4 x500 Custom
=====================================================
Controls the quadcopter in Offboard mode using a DualShock 4 (PS4) controller.

Requirements:
    sudo apt install ros-humble-joy
    pip install transforms3d

Run:
    Terminal 1: ros2 run joy joy_node                      # reads the DS4
    Terminal 2: python3 ds4_offboard_controller.py         # this script

DualShock 4 Button Map (linux joy node):
    Button 0  : X (Cross)     -> ARM
    Button 1  : O (Circle)    -> DISARM
    Button 2  : Triangle      -> TAKEOFF (fly to 1.5m)
    Button 3  : Square        -> LAND
    Button 9  : Options       -> ENABLE OFFBOARD MODE
    Button 4  : L1            -> (reserved)
    Button 5  : R1            -> (reserved)

DualShock 4 Axis Map:
    Axis 0 : Left  stick X  -> Yaw rate         (left/right)
    Axis 1 : Left  stick Y  -> Altitude velocity (up/down) [inverted]
    Axis 3 : Right stick X  -> Lateral velocity  (strafe left/right)
    Axis 4 : Right stick Y  -> Forward velocity  (forward/back) [inverted]
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleStatus,
)
from sensor_msgs.msg import Joy

import math

# ── Tuning Parameters ────────────────────────────────────────────────────────

MAX_VEL_XY    = 5.0     # m/s   max horizontal velocity
MAX_VEL_Z     = 2.0     # m/s   max vertical velocity
MAX_YAW_RATE  = 1.5     # rad/s max yaw rate
DEADZONE       = 0.08   # ignore stick deflections below this value
TAKEOFF_ALT   = -1.5    # NED altitude for takeoff (negative = up)

# ── DS4 Axis/Button Indices ───────────────────────────────────────────────────

AXIS_YAW       = 0
AXIS_THROTTLE  = 1   # inverted
AXIS_STRAFE    = 3
AXIS_FORWARD   = 4   # inverted

BTN_ARM        = 0   # Cross
BTN_DISARM     = 1   # Circle
BTN_TAKEOFF    = 2   # Triangle
BTN_LAND       = 3   # Square
BTN_OFFBOARD   = 9   # Options

# ─────────────────────────────────────────────────────────────────────────────


def deadzone(val: float, dz: float) -> float:
    """Apply a deadzone to a joystick axis value."""
    if abs(val) < dz:
        return 0.0
    return (val - math.copysign(dz, val)) / (1.0 - dz)


class DS4OffboardController(Node):

    def __init__(self):
        super().__init__('ds4_offboard_controller')

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )

        # ── Publishers ───────────────────────────────────────────────────────
        self.offboard_pub  = self.create_publisher(OffboardControlMode, '/fmu/in/offboard_control_mode', qos)
        self.setpoint_pub  = self.create_publisher(TrajectorySetpoint,   '/fmu/in/trajectory_setpoint',  qos)
        self.cmd_pub       = self.create_publisher(VehicleCommand,        '/fmu/in/vehicle_command',      qos)

        # ── Subscribers ──────────────────────────────────────────────────────
        self.joy_sub    = self.create_subscription(Joy,           '/joy',                         self.joy_callback,    10)
        self.status_sub = self.create_subscription(VehicleStatus, '/fmu/out/vehicle_status',      self.status_callback, qos)

        # ── State ─────────────────────────────────────────────────────────────
        self.armed          = False
        self.offboard_mode  = False
        self.nav_state      = 0

        # Velocity setpoints (NED frame)
        self.vx = 0.0   # forward
        self.vy = 0.0   # right
        self.vz = 0.0   # down (negative = up)
        self.yaw_rate = 0.0

        # Current yaw heading (for yaw-rate control)
        self.current_yaw = 0.0

        # Track previous button states to detect rising edges only
        self.prev_buttons = []

        # ── Heartbeat timer (must stream at ≥2Hz for Offboard to stay active)
        self.counter = 0
        self.timer = self.create_timer(0.05, self.timer_callback)  # 20 Hz

        self.get_logger().info("DS4 Offboard Controller ready.")
        self.get_logger().info("Connect DS4, then press OPTIONS to enable Offboard mode.")
        self.get_logger().info("Press X to ARM, Triangle to TAKEOFF, Square to LAND, O to DISARM.")

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def status_callback(self, msg: VehicleStatus):
        self.armed     = msg.arming_state == VehicleStatus.ARMING_STATE_ARMED
        self.nav_state = msg.nav_state

    def joy_callback(self, msg: Joy):
        axes    = msg.axes
        buttons = list(msg.buttons)

        # Pad prev_buttons on first callback
        if not self.prev_buttons:
            self.prev_buttons = [0] * len(buttons)

        def pressed(idx):
            """Returns True only on the rising edge (button just pressed)."""
            return buttons[idx] == 1 and self.prev_buttons[idx] == 0

        # ── Button Actions (rising-edge only) ────────────────────────────────

        if pressed(BTN_OFFBOARD):
            self.get_logger().info("OPTIONS pressed → Switching to Offboard mode")
            self.set_offboard_mode()

        if pressed(BTN_ARM):
            self.get_logger().info("X pressed → Arming")
            self.arm()

        if pressed(BTN_DISARM):
            self.get_logger().info("O pressed → Disarming")
            self.disarm()

        if pressed(BTN_TAKEOFF):
            self.get_logger().info(f"Triangle pressed → Takeoff to {abs(TAKEOFF_ALT)}m")
            self.takeoff()

        if pressed(BTN_LAND):
            self.get_logger().info("Square pressed → Landing")
            self.land()

        # ── Stick → Velocity Setpoints ───────────────────────────────────────

        raw_forward  = axes[AXIS_FORWARD]   if len(axes) > AXIS_FORWARD  else 0.0
        raw_strafe   = axes[AXIS_STRAFE]    if len(axes) > AXIS_STRAFE   else 0.0
        raw_throttle = axes[AXIS_THROTTLE]  if len(axes) > AXIS_THROTTLE else 0.0
        raw_yaw      = axes[AXIS_YAW]       if len(axes) > AXIS_YAW      else 0.0

        # Apply deadzone and scale (DS4 Y-axes are inverted → negate)
        self.vx        =  deadzone(-raw_forward,  DEADZONE) * MAX_VEL_XY
        self.vy        = -deadzone(raw_strafe,    DEADZONE) * MAX_VEL_XY
        self.vz        =  deadzone(-raw_throttle, DEADZONE) * MAX_VEL_Z
        self.yaw_rate  = -deadzone(raw_yaw,       DEADZONE) * MAX_YAW_RATE

        self.prev_buttons = buttons

    def timer_callback(self):
        """Stream offboard heartbeat and setpoints at 20 Hz."""
        self.publish_offboard_mode()
        self.publish_setpoint()
        self.counter += 1

    # ── PX4 Command Helpers ───────────────────────────────────────────────────

    def publish_offboard_mode(self):
        msg = OffboardControlMode()
        msg.position     = False
        msg.velocity     = True
        msg.acceleration = False
        msg.attitude     = False
        msg.body_rate    = False
        msg.timestamp    = int(self.get_clock().now().nanoseconds / 1000)
        self.offboard_pub.publish(msg)

    def publish_setpoint(self):
        msg = TrajectorySetpoint()
        msg.position     = [float('nan'), float('nan'), float('nan')]
        msg.velocity     = [self.vx, self.vy, self.vz]
        msg.yawspeed     = self.yaw_rate
        msg.yaw          = float('nan')
        msg.timestamp    = int(self.get_clock().now().nanoseconds / 1000)
        self.setpoint_pub.publish(msg)

    def send_vehicle_command(self, command, param1=0.0, param2=0.0):
        msg = VehicleCommand()
        msg.command          = command
        msg.param1           = float(param1)
        msg.param2           = float(param2)
        msg.target_system    = 1
        msg.target_component = 1
        msg.source_system    = 1
        msg.source_component = 1
        msg.from_external    = True
        msg.timestamp        = int(self.get_clock().now().nanoseconds / 1000)
        self.cmd_pub.publish(msg)

    def arm(self):
        self.send_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)

    def disarm(self):
        self.send_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=0.0)

    def set_offboard_mode(self):
        self.send_vehicle_command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, param1=1.0, param2=6.0)

    def takeoff(self):
        """Switch to position mode setpoint at takeoff altitude."""
        msg = TrajectorySetpoint()
        msg.position  = [0.0, 0.0, TAKEOFF_ALT]
        msg.yaw       = 0.0
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.setpoint_pub.publish(msg)

    def land(self):
        self.send_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)


def main(args=None):
    rclpy.init(args=args)
    node = DS4OffboardController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
