#!/usr/bin/env python3
"""
pf_mecanum_gamepad_drive.py

Drive PathfinderBot with a Logitech F710 wireless gamepad.

- Left stick Y:   tank-style control for LEFT side (forward/back)
- Right stick Y:  tank-style control for RIGHT side (forward/back)
- Left/Right X:   mecanum strafe left/right (we average both X axes)
- Right trigger:  analog drive forward (both sides)
- Left trigger:   analog drive backward (both sides)
- Right bumper:   turn right in place
- Left bumper:    turn left in place
- 'A' button:     look_forward (arm/camera pose)
- 'B' button:     pickup_block (arm pickup sequence)
- 'Back' button:  all-stop
- 'Start' button: quit program

Make sure the F710 is in **X** mode (switch on the back) and its
nano-receiver is plugged into the Pi.

Requires:
    sudo apt-get install python3-pygame
    # or:
    # pip3 install pygame
"""

import math
import sys
import time
import random


import pygame
import Board  # For servos / arm control

# Sonar (ultrasonic + 2 RGB LEDs on the sensor)
try:
    from Sonar import Sonar
    _SONAR_AVAILABLE = True
except Exception as e:
    Sonar = None
    _SONAR_AVAILABLE = False
    print(f"[WARN] Sonar module not available: {e}")

from mecanum import MecanumChassis as Mecanum
from pf_start_robot import initialize_robot

# ----- Tunable constants -----
MAX_LINEAR_SPEED = 80.0   # mm/s, similar scale to web driver
MAX_ROT_SPEED    = 50.0   # base turn speed
ROT_SCALE        = 0.008  # same as pf_mecanum_web_drive
DEADZONE         = 0.15   # ignore tiny joystick noise

# Trigger / bumper behavior
TRIGGER_DRIVE_VALUE = 1.0   # max forward/back scale (0..1), multiplied by MAX_LINEAR_SPEED
BUMPER_TURN_VALUE   = 0.8   # how hard bumpers turn (0..1)
TRIGGER_THRESHOLD   = 0.1   # minimal analog trigger magnitude to count as "pressed"

# ----- Sonar / LED behavior -----
# Right stick button (R3) enables sonar display; Left stick button (L3) disables it.
# Distances are in millimeters (mm).
SONAR_DISTANCE_THRESHOLD_MM = 305   # ~1 ft: red when closer than this
SONAR_CAUTION_THRESHOLD_MM  = 610   # ~2 ft: yellow when between 1–2 ft, green when beyond
SONAR_CHECK_INTERVAL_SEC    = 0.10  # how often to read distance
SONAR_RANDOM_COLOR_SEC      = 0.50  # how often to randomize the sonar LEDs

# These axis indices are typical for the F710 in XInput mode on Linux.
# If movement is weird, run a small debug script to print all axes and adjust.
AXIS_LX = 0
AXIS_LY = 1
AXIS_LT = 2  # left trigger (usually)
AXIS_RX = 3
AXIS_RY = 4
AXIS_RT = 5  # right trigger (usually)

# Button indices (these are common for XInput-style controllers)
BTN_A     = 0
BTN_B     = 1
BTN_X     = 2
BTN_Y     = 3
BTN_LB    = 4
BTN_RB    = 5
BTN_BACK  = 6
BTN_START = 7
BTN_LS = 10  # Left stick press (L3)  <-- from your test
BTN_RS = 9   # Right stick press (R3) <-- from your test

# BTN_GUIDE = 10  # (Optional) Logitech / Guide button if exposed by your OS


# ----- Arm / camera poses (from pf_April_nav_web_drive_store.py) -----
def look_forward():
    Board.setPWMServoPulse(1, 1500, 500)
    Board.setPWMServoPulse(3, 700, 1000)
    Board.setPWMServoPulse(4, 2425, 1000)
    Board.setPWMServoPulse(5, 790, 1000)
    Board.setPWMServoPulse(6, 1500, 1000)
    time.sleep(1)

def look_sad():
    #Board.setPWMServoPulse(1, 1500, 500)
    Board.setPWMServoPulse(3, 800, 1000)
    Board.setPWMServoPulse(4, 2500, 1000)
    Board.setPWMServoPulse(5, 1900, 1000)
    Board.setPWMServoPulse(6, 1500, 1000)
    time.sleep(.5)
    Board.setPWMServoPulse(3, 600, 1000)

    
def say_yes():
    Board.setPWMServoPulse(4, 2425, 1000)
    Board.setPWMServoPulse(5, 790, 1000)
    Board.setPWMServoPulse(3, 590, 2000)
    time.sleep(0.2)
    Board.setPWMServoPulse(3, 500, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(3, 800, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(3, 500, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(3, 800, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(3, 590, 200)
    time.sleep(0.2)

def say_no():
    Board.setPWMServoPulse(4, 2425, 1000)
    Board.setPWMServoPulse(5, 790, 1000)
    time.sleep(0.2)
    Board.setPWMServoPulse(6, 1300, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(6, 1700, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(6, 1300, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(6, 1700, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(6, 1500, 200)
    time.sleep(0.2)

def pickup_block():
    Board.setPWMServoPulse(1, 1500, 2000)
    Board.setPWMServoPulse(3, 590, 2000)
    Board.setPWMServoPulse(4, 2500, 2000)
    Board.setPWMServoPulse(5, 700, 2000)
    Board.setPWMServoPulse(6, 1500, 2000)

    Board.setPWMServoPulse(5, 1818, 1000)
    time.sleep(1)
    Board.setPWMServoPulse(4, 2023, 300)
    Board.setPWMServoPulse(5, 2091, 300)
    time.sleep(0.3)
    Board.setPWMServoPulse(1, 1932, 400)
    time.sleep(0.4)
    Board.setPWMServoPulse(3, 750, 800)
    Board.setPWMServoPulse(5, 2364, 800)
    time.sleep(0.8)
    Board.setPWMServoPulse(1, 1455, 300)
    Board.setPWMServoPulse(5, 2318, 300)
    time.sleep(0.3)
    Board.setPWMServoPulse(5, 1841, 1000)
    time.sleep(1)
    look_forward()


def left_pickup_block():
    Board.setPWMServoPulse(1, 2020, 1000)
    Board.setPWMServoPulse(3, 800, 1000)
    Board.setPWMServoPulse(4, 2020, 1000)
    Board.setPWMServoPulse(5, 2091, 1000)
    Board.setPWMServoPulse(6, 2500, 1000)
    time.sleep(1)
    Board.setPWMServoPulse(3, 900, 800)
    Board.setPWMServoPulse(5, 2364, 800)
    time.sleep(0.8)
    Board.setPWMServoPulse(1, 1455, 500)
    Board.setPWMServoPulse(5, 2300, 300)
    time.sleep(0.3)
    Board.setPWMServoPulse(5, 1841, 1000)

    time.sleep(1)
    look_forward()

def right_pickup_block():
    Board.setPWMServoPulse(1, 2020, 1000)
    Board.setPWMServoPulse(3, 800, 1000)
    Board.setPWMServoPulse(4, 1800, 1000)
    Board.setPWMServoPulse(5, 2091, 1000)
    Board.setPWMServoPulse(6, 500, 1000)
    time.sleep(1)
    Board.setPWMServoPulse(3, 800, 800)
    Board.setPWMServoPulse(5, 2450, 800)
    time.sleep(0.8)
    Board.setPWMServoPulse(1, 1455, 500)
    Board.setPWMServoPulse(5, 2318, 300)

    time.sleep(0.3)
    Board.setPWMServoPulse(5, 1841, 1000)

    time.sleep(1)
    look_forward()

def backward_drop_block():
    Board.setPWMServoPulse(1, 1500, 2000)
    Board.setPWMServoPulse(3, 2500, 2000)
    Board.setPWMServoPulse(4, 500, 2000)
    Board.setPWMServoPulse(5, 1636, 2000)
    time.sleep(2)
    Board.setPWMServoPulse(1, 2020, 2000)
    time.sleep(2.1)
    look_forward()



# ----- Sonar + LED helpers -----
def _robot_led_set(color):
    """Set the *robot's* on-board RGB LED (if present in this firmware)."""
    try:
        # Common Hiwonder Board API: Board.RGB.setPixelColor + Board.RGB.show()
        if hasattr(Board, 'RGB') and hasattr(Board.RGB, 'setPixelColor'):
            Board.RGB.setPixelColor(0, color)
            Board.RGB.show()
            return
        # Fallbacks (some firmwares expose these directly)
        if hasattr(Board, 'setPixelColor'):
            Board.setPixelColor(0, color)
            if hasattr(Board, 'show'):
                Board.show()
    except Exception as e:
        # Don’t let LED issues break driving
        print(f"[WARN] Robot LED update failed: {e}")


def _sonar_led_randomize(sonar):
    """Randomize the two RGB LEDs on the sonar sensor."""
    try:
        c0 = Board.PixelColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        c1 = Board.PixelColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        sonar.setPixelColor(0, c0)
        sonar.setPixelColor(1, c1)
        sonar.show()
    except Exception as e:
        print(f"[WARN] Sonar LED update failed: {e}")


def _sonar_led_off(sonar):
    """Turn off sonar LEDs."""
    try:
        off = Board.PixelColor(0, 0, 0)
        sonar.setPixelColor(0, off)
        sonar.setPixelColor(1, off)
        sonar.show()
    except Exception:
        pass


def _robot_led_from_distance(distance_mm: float):
    """Map sonar distance to robot LED color: green (far), yellow (mid), red (close)."""
    try:
        d = float(distance_mm)
    except Exception:
        return

    if d >= SONAR_CAUTION_THRESHOLD_MM:
        color = Board.PixelColor(0, 255, 0)      # Green
    elif d >= SONAR_DISTANCE_THRESHOLD_MM:
        color = Board.PixelColor(255, 255, 0)    # Yellow
    else:
        color = Board.PixelColor(255, 0, 0)      # Red

    _robot_led_set(color)

# ----- Helpers for drive logic -----
def apply_deadzone(value: float, dz: float = DEADZONE) -> float:
    """Clamp small values to zero to avoid drift."""
    return 0.0 if abs(value) < dz else value


def normalize_trigger(raw: float) -> float:
    """Map trigger axis to 0..1, handling both [-1..1] and [0..1] styles.

    For many F710 mappings:
    - Rest is either -1 or 0
    - Fully pressed is 1
    """
    # Clamp to sane range first
    if raw <= 0.0:
        # Treat as [-1..1] style: -1 -> 0, 0 -> 0.5, 1 -> 1 (if ever)
        val = (raw + 1.0) / 2.0
    else:
        # Treat as [0..1] style
        val = raw
    # Final clamp 0..1
    if val < 0.0:
        return 0.0
    if val > 1.0:
        return 1.0
    return val


def init_gamepad() -> pygame.joystick.Joystick:
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        print("No gamepads detected. Is the F710 receiver plugged in?")
        sys.exit(1)

    js = pygame.joystick.Joystick(0)
    js.init()
    print(f"Using gamepad: {js.get_name()} with {js.get_numaxes()} axes and {js.get_numbuttons()} buttons.")
    return js


def drive_loop(bot: Mecanum, js: pygame.joystick.Joystick):
    """Main loop: read joystick and send commands to mecanum drive."""
    running = True

    # Sonar display state (distance -> robot LED, random colors on sonar LEDs)
    sonar_enabled = False
    sonar = None
    last_sonar_check = 0.0
    last_sonar_rand  = 0.0

    try:
        while running:
            # Process events (needed for pygame to update joystick state)
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    if js.get_button(BTN_A):
                        print("[A] Look forward pose")
                        look_forward()

                    if js.get_button(BTN_B):
                        print("[B] Pickup block sequence")
                        look_sad()
                        

                    if js.get_button(BTN_Y):
                        print("[Y] say yes sequence")
                        say_yes()

                    if js.get_button(BTN_X):
                        print("[B] say no sequence")
                        say_no()

                    if js.get_button(BTN_BACK):
                        print("[Back] STOP")
                        bot.reset_motors()

                    if js.get_button(BTN_START):
                        print("[Start] Quit requested")
                        running = False


                        # Sonar toggle: R3 = ON, L3 = OFF
                        if js.get_button(BTN_RS):
                            if not _SONAR_AVAILABLE:
                                print("[R3] Sonar not available on this image (missing Sonar module).")
                            else:
                                if sonar is None:
                                    print("[R3] Initializing Sonar...")
                                    sonar = Sonar()
                                    sonar.setRGBMode(0)  # solid/static mode
                                sonar_enabled = True
                                last_sonar_check = 0.0
                                last_sonar_rand  = 0.0
                                print("[R3] Sonar display ON")

                        if js.get_button(BTN_LS):
                            sonar_enabled = False
                            if sonar is not None:
                                _sonar_led_off(sonar)
                            _robot_led_set(Board.PixelColor(0, 0, 0))
                            print("[L3] Sonar display OFF")

                # --- D-PAD (HAT) ---
                if event.type == pygame.JOYHATMOTION:
                    hat_x, hat_y = js.get_hat(0)

                    # D-pad up (forward) is usually (0, 1)
                    if hat_x == 0 and hat_y == 1:
                        print("D-pad UP pressed")
                        pickup_block()

                    if hat_x == 0 and hat_y == -1:  # DOWN
                        print("D-pad DOWN pressed")
                        backward_drop_block()
                        
                    if hat_x == -1 and hat_y == 0:  # LEFT
                        print("D-pad LEFT pressed")
                        left_pickup_block()
                        
                    if hat_x == 1 and hat_y == 0:   # RIGHT
                        print("D-pad RIGHT pressed")
                        right_pickup_block()



            # Read stick axes
            left_x  = apply_deadzone(js.get_axis(AXIS_LX))
            left_y  = -apply_deadzone(js.get_axis(AXIS_LY))  # invert so up=+
            right_x = apply_deadzone(js.get_axis(AXIS_RX))
            right_y = -apply_deadzone(js.get_axis(AXIS_RY))  # invert so up=+

            # Tank-style inputs, adjusted so LEFT stick drives LEFT motors,
            # and RIGHT stick drives RIGHT motors to match your wiring.
            left_track  = right_y   # swapped
            right_track = left_y    # swapped

            # Base forward/back and turn from sticks
            forward_cmd = (left_track + right_track) / 2.0
            turn_cmd    = (right_track - left_track) / 2.0

            # Strafe (mecanum) is the average of both X axes
            strafe_cmd = (left_x + right_x) / 2.0

            # ----- Triggers & bumpers (analog overrides) -----
            lt_raw = js.get_axis(AXIS_LT)
            rt_raw = js.get_axis(AXIS_RT)

            lt_mag = normalize_trigger(lt_raw)
            rt_mag = normalize_trigger(rt_raw)

            lt_active = lt_mag > TRIGGER_THRESHOLD
            rt_active = rt_mag > TRIGGER_THRESHOLD

            # Bumpers are digital buttons
            lb_pressed = js.get_button(BTN_LB)
            rb_pressed = js.get_button(BTN_RB)

            # Right trigger: analog forward (both sides)
            # Left trigger: analog backward (both sides)
            if rt_active and not lt_active:
                forward_cmd = rt_mag * TRIGGER_DRIVE_VALUE
            elif lt_active and not rt_active:
                forward_cmd = -lt_mag * TRIGGER_DRIVE_VALUE
            # If both triggers or neither are active, leave stick-based forward_cmd alone.

            # Right bumper: turn right, Left bumper: turn left.
            # Sign here just controls direction; flip if it feels backwards.
            if rb_pressed and not lb_pressed:
                turn_cmd = BUMPER_TURN_VALUE
            elif lb_pressed and not rb_pressed:
                turn_cmd = -BUMPER_TURN_VALUE
            # If both bumpers or neither are active, keep stick-based turn_cmd.

            # Convert to chassis velocities
            vx = strafe_cmd * MAX_LINEAR_SPEED   # left/right
            vy = forward_cmd * MAX_LINEAR_SPEED  # forward/back
            omega = turn_cmd * MAX_ROT_SPEED * ROT_SCALE

            # If everything is near zero, stop the motors
            if (abs(vx) < 1.0 and abs(vy) < 1.0 and abs(omega) < 0.001):
                bot.reset_motors()
            else:
                # Use mecanum.translation(fake=True) to compute (velocity, direction)
                # then feed that into set_velocity with our angular rate.
                velocity, direction = bot.translation(vx, vy, fake=True)
                bot.set_velocity(velocity, direction, omega)


            # ----- Sonar background update (does not affect driving) -----
            if sonar_enabled and sonar is not None:
                now = time.time()
                # Read distance and set *robot* LED based on distance
                if (now - last_sonar_check) >= SONAR_CHECK_INTERVAL_SEC:
                    last_sonar_check = now
                    try:
                        dist_mm = sonar.getDistance()
                    except Exception as e:
                        print(f"[WARN] Sonar read failed: {e}")
                        sonar_enabled = False
                        _sonar_led_off(sonar)
                        _robot_led_set(Board.PixelColor(0, 0, 0))
                    else:
                        _robot_led_from_distance(dist_mm)

                # Randomize the *sonar* LEDs for fun / visibility
                if (now - last_sonar_rand) >= SONAR_RANDOM_COLOR_SEC:
                    last_sonar_rand = now
                    _sonar_led_randomize(sonar)
            time.sleep(0.02)  # ~50 Hz update rate

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt: stopping robot.")
    finally:
        bot.reset_motors()
        # Clean up LEDs if sonar was enabled
        try:
            if 'sonar' in locals() and sonar is not None:
                _sonar_led_off(sonar)
            _robot_led_set(Board.PixelColor(0, 0, 0))
        except Exception:
            pass

        pygame.joystick.quit()
        pygame.quit()


def main():
    print("Initializing PathfinderBot hardware...")
    initialize_robot()
    bot = Mecanum()

    print("Initializing Logitech F710 gamepad...")
    js = init_gamepad()

    print("Gamepad control ready. "
          "Sticks = tank/strafe, triggers = analog forward/back, bumpers = turn, "
          "A = look_forward, B = pickup_block, R3 = sonar ON, L3 = sonar OFF.")
    drive_loop(bot, js)


if __name__ == "__main__":
    main()
