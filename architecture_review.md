# System Architecture & Risk Analysis (Murphy's Law)

**Proposed Hardware:**
* **Flight Controller (FCU):** Pixhawk 6C
* **Companion Computer (CC):** Raspberry Pi 4 (8GB)
* **Main Navigation:** Benewake TFMini-S (Micro LiDAR, Forward)
* **Precision Landing/Ground Alt:** GY-53 VL53L0X (Bottom) + USB Cam (Bottom)
* **Obstacle Detection:** Pi Camera Rev 1.3 (Forward, running MobileNet v2/v3)
* **Close Proximity Ring:** 5x HC-SR04 (Ultrasonics: Top, Front, Back, Left, Right)

---

## 🚨 Murphy’s Law: What Will Go Wrong 🚨

If anything can go wrong with a custom drone, it will. Here is an aggressive analysis of the "hiccups" and critical failures you are likely to face with this specific combination of hardware and algorithms.

### 1. Compute Bottleneck: The Raspberry Pi 4 vs. MobileNet
You plan to run MobileNet v2/v3 on a Raspberry Pi 4 for forward obstacle detection. 
* **The Hiccup:** The Pi 4 CPU will choke. Running MobileNet v2/v3 natively on the Pi’s ARM cores (even the 8GB model) will likely yield **5 - 12 FPS** at best.
* **The Consequence:** If the drone is flying forward at 5 m/s, and your camera only detects a person every 200 milliseconds, the drone travels an entire meter between frames. It **will** crash into thin obstacles before the code has time to send an emergency brake command via MAVLink to the Pixhawk.
* **The Fix:** Hardware acceleration is required. **[RESOLVED]** You confirmed you are using explicitly lightweight models (`YOLOv8n`), which the Pi 4 can process at a borderline-acceptable framerate without crashing, though a Coral TPU is still highly recommended for real-time safety.

### 2. Sensor Interference: The HC-SR04 Array
You plan to run five HC-SR04 ultrasonic sensors simultaneously.
* **The Hiccup:** Acoustic Crosstalk. If all five sonars pulse at the same time, the "ping" from the left sensor bouncing off a wall can be received by the front sensor. 
* **The Consequence:** The flight controller will suddenly receive garbage data stating an obstacle is 0.1m in front of it when it’s actually 3.5m to the left. The drone will exhibit violently unpredictable twitches and emergency stops in mid-air.
* **The Fix:** You must **multiplex** the trigger pins. 

### How Multiplexing 5x HC-SR04s Works
Multiplexing means you intentionally write a Python script (or use a dedicated microcontroller like an Arduino Nano) to only fire one sensor at a time in a continuous loop. 
1. **The Physics:** Sound travels roughly 343 m/s. If an object is at your max range of 4 meters, it takes the sound ~11ms to hit the object and another ~11ms to bounce back. 
2. **The Delay:** If you fire the Front sensor, you must force the script to `sleep` for at least 30-40 milliseconds to allow all residual sound waves (echoes) in the room to completely dissipate.
3. **The Loop:** After 40ms, you fire the Right sensor. Wait 40ms. Fire the Back sensor. Wait 40ms.
4. **The Bottleneck:** Because you have to wait for sound to travel for 5 separate sensors, your entire 360-degree obstacle reading will only update at ~5Hz (5 times a second). If you fire them any faster, they will hear each other and crash the drone.

### 3. The "Black Hole" Effect: Downward Optical Flow & Landing
You have a bottom-facing VL53L0X (Max 2m range) and a bottom USB camera (presumably for Optical Flow / Precision Landing).
* **The Hiccup:** The VL53L0X only works up to 2 meters. If you switch into Position/Altitude Hold mode above 2 meters without a strong GPS lock or a longer-range rangefinder, the EKF2 (PX4's estimator) will instantly drop the altitude reading because the VL53L0X will report "Out of Range" (infinity).
* **The Consequence:** The drone will think it is infinitely high and will rapidly drop out of the sky until it crosses the 2m threshold, at which point it will violently brake (if it doesn't slam into the ground first). Furthermore, Optical Flow cameras fail completely over featureless surfaces (like smooth black asphalt or unmarked white floors).
* **The Fix:** **[RESOLVED]** You confirmed the Barometer is set as the primary altitude source. The VL53L0X will strictly act as a distance sensor for the final 2 meters of landing.

### 4. UART Saturation: The TFMini-S vs. Pixhawk
The TFMini-S is your main forward navigation tool, likely running over a Serial UART to the Pixhawk.
* **The Hiccup:** Noise and bad shielding. Long, unshielded wires picking up electromagnetic interference (EMI) from the high-current ESCs and motors.
* **The Consequence:** The I2C/UART bus will drop packets. The Pixhawk might enter a failsafe mode if it loses the main rangefinder reading for more than a second, causing an unexpected Return-To-Launch (RTL) or auto-land sequence directly into a tree.
* **The Fix:** **[RESOLVED]** You confirmed the use of shielded/twisted cables for the UART runs.

### 5. Vibration: The "Jello" Cams
You have a Pi Cam and a USB Cam hard-mounted to an x500 frame.
* **The Hiccup:** The x500 carbon fiber frame transmits extreme, high-frequency motor vibrations directly into the camera lenses.
* **The Consequence:** The resulting video will have extreme "Jello" (Rolling Shutter effect). MobileNet relies on crisp edges to identify shapes. If the image is warped by vibration, the neural network's confidence scores will plummet, and it won't detect obvious obstacles.
* **The Fix:** **[RESOLVED]** Both cameras are mounted using vibration dampeners.

### 6. The Pi 4 Power Draw
The Pixhawk 6C is extremely reliable, but the Raspberry Pi 4 is a power hog (up to 3A at 5V under heavy MobileNet load).
* **The Hiccup:** Pulling power for the Pi 4 directly from the same 5V BEC/Power Module that feeds the Pixhawk or the receiver.
* **The Consequence:** Under heavy load, the Pi 4 will cause a voltage drop (brownout). If the 5V rail dips to 4.5V, the Pixhawk will instantaneously reboot mid-flight. No errors, no warnings, just a 2kg rock falling from the sky.
* **The Fix:** **[RESOLVED]** You confirmed the Pi 4 is externally powered using a dedicated 5V/5A DC-DC converter, completely isolating it from the Pixhawk's power plane.

---

Based on your hardware confirmations, the primary remaining hurdle is software-based:
* **Custom Multiplexer Script/Arduino:** Mandatory to prevent the 5 HC-SR04s from blinding each other via acoustic crosstalk.
