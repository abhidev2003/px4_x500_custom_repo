#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import math

# =======================================================================
# HC-SR04 Multiplexing Script for Raspberry Pi 4
# -----------------------------------------------------------------------
# This script sequentially triggers 5 ultrasonic sensors to prevent 
# acoustic crosstalk. It publishes the distances to PX4 via MAVLink 
# or ROS 2 (customizable in the publish_distance function).
# =======================================================================

# Define the BCM GPIO pins for each sensor
# UPDATE THESE TO MATCH YOUR PHYSICAL WIRING
SENSORS = {
    "Front": {"TRIG": 17, "ECHO": 27},
    "Back":  {"TRIG": 22, "ECHO": 23},
    "Left":  {"TRIG": 24, "ECHO": 25},
    "Right": {"TRIG": 5,  "ECHO": 6},
    "Top":   {"TRIG": 12, "ECHO": 16}
}

# The speed of sound is ~34300 cm/s
SPEED_OF_SOUND_CM_S = 34300

# Constants for timeouts and delays
MAX_DISTANCE_CM = 400.0  # HC-SR04 max reliable range is 4m
TIMEOUT_S = (MAX_DISTANCE_CM * 2) / SPEED_OF_SOUND_CM_S # Max time to wait for a 4m return echo
ECHO_DECAY_DELAY_S = 0.04  # 40ms wait between firing different sensors allows stray sound to dissipate

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for name, pins in SENSORS.items():
        GPIO.setup(pins["TRIG"], GPIO.OUT)
        GPIO.setup(pins["ECHO"], GPIO.IN)
        GPIO.output(pins["TRIG"], GPIO.LOW)
    print("GPIO Setup Complete. Waiting for sensors to settle...")
    time.sleep(1)

def measure_distance(name, trig_pin, echo_pin):
    # 1. Send the 10 microsecond trigger pulse
    GPIO.output(trig_pin, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(trig_pin, GPIO.LOW)

    # 2. Record the timeout boundaries
    pulse_start = time.time()
    pulse_end = time.time()
    timeout_start = pulse_start

    # 3. Wait for the ECHO pin to go HIGH (Start of pulse)
    while GPIO.input(echo_pin) == 0:
        pulse_start = time.time()
        if pulse_start - timeout_start > TIMEOUT_S:
            return float('inf') # Timed out waiting for signal to start

    # 4. Wait for the ECHO pin to go LOW (End of pulse return)
    while GPIO.input(echo_pin) == 1:
        pulse_end = time.time()
        if pulse_end - pulse_start > TIMEOUT_S:
            return float('inf') # Timed out waiting for signal to return

    # 5. Calculate physical distance
    pulse_duration = pulse_end - pulse_start
    distance_cm = (pulse_duration * SPEED_OF_SOUND_CM_S) / 2
    
    return round(distance_cm, 1)

def publish_distance(sensor_name, distance_cm):
    """
    TODO: Add MAVLink (pymavlink) or ROS 2 (rclpy) publishing logic here.
    For now, we just print the result to the console.
    """
    if math.isinf(distance_cm):
         print(f"[{sensor_name}]: OUT OF RANGE (>4m)")
    else:
         print(f"[{sensor_name}]: {distance_cm} cm")

def run_multiplexer_loop():
    try:
        while True:
            # Sequentially loop through each sensor
            for name, pins in SENSORS.items():
                
                # Take the measurement
                dist = measure_distance(name, pins["TRIG"], pins["ECHO"])
                
                # Publish the measurement
                publish_distance(name, dist)
                
                # CRITICAL: Wait for the sound wave to completely decay in the room
                # before firing the next sensor in the array
                time.sleep(ECHO_DECAY_DELAY_S)
                
            print("-" * 20)

    except KeyboardInterrupt:
        print("\nMultiplexer stopped by user.")
    finally:
        GPIO.cleanup()

if __name__ == '__main__':
    setup_gpio()
    run_multiplexer_loop()
