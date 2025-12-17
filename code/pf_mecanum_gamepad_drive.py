#!/usr/bin/env python
"""
pf_mecanum_gamepad_drive.py

Drive PathfinderBot with a Logitech F710 wireless gamepad.

Notes:
- Recommended: set the F710 switch to **X** (XInput) on the back of the controller.
- This script intentionally swaps the left/right stick Y mapping to match the robot's motor wiring.

Controls
- Left stick Y:   RIGHT-side track forward/back (swapped)
- Right stick Y:  LEFT-side track forward/back (swapped)
- Left/Right X:   mecanum strafe left/right (average of both X axes)
- Right trigger:  analog drive forward (both sides)
- Left trigger:   analog drive backward (both sides)
- Right bumper:   turn right in place
- Left bumper:    turn left in place

Actions
- A button:       look_forward (arm/camera pose)
- B button:       look_sad (expression)
- X button:       say_no
- Y button:       say_yes
- Logitech button: look_around
- D-pad UP:       pickup_block
- D-pad DOWN:     backward_drop_block
- D-pad LEFT:     left_pickup_block
- D-pad RIGHT:    right_pickup_block
- Back button:    all-stop (motors off)
- Start button:   quit program
Requires:
    pygame (install via your OS package manager or pip)

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
SONAR_DISTANCE_THRESHOLD_MM = 203   # ~8 inches red when closer than this
SONAR_CAUTION_THRESHOLD_MM  = 406   # ~16 inches: yellow when between 8 and 16 inches, green when beyond
SONAR_CHECK_INTERVAL_SEC    = 0.10  # how often to read distance
SONAR_RANDOM_COLOR_SEC      = 0.50  # how often to randomize the sonar LEDs

# "Critical" zone: 4 inches or less (strong rumble + fast flashing + sonar LEDs red)
SONAR_CRITICAL_THRESHOLD_MM      = 75   # ~3 inches
SONAR_CRITICAL_FLASH_INTERVAL_SEC = 0.08  # faster flash when critical
SONAR_CRITICAL_RUMBLE_COOLDOWN_SEC = 0.35 # more frequent pulses when critical
SONAR_CRITICAL_RUMBLE_DURATION_MS  = 200  # pulse length (ms)
SONAR_CRITICAL_RUMBLE_LOW          = 1.00 # strong low-frequency motor
SONAR_CRITICAL_RUMBLE_HIGH         = 1.00 # strong high-frequency motor



# Beeps (robot buzzer) for proximity alerts
# - Short beep when <= 1 ft
# - Rapid beeps when <= 4 in (critical)
SONAR_BEEP_COOLDOWN_SEC          = 1.00  # min time between short beeps (<= 1 ft)
SONAR_BEEP_DURATION_SEC          = 0.08  # short beep length

SONAR_CRITICAL_BEEP_INTERVAL_SEC = 0.15  # rapid beep rate when critical (<= 4 in)
SONAR_CRITICAL_BEEP_DURATION_SEC = 0.05  # rapid beep length
# Extra feedback when we're in the "too close" zone (red)
SONAR_FLASH_INTERVAL_SEC    = 0.20  # robot LED flashes red/off this often when too close
SONAR_RUMBLE_COOLDOWN_SEC   = 1.00  # minimum time between rumble pulses
SONAR_RUMBLE_DURATION_MS    = 250   # how long each rumble pulse lasts
SONAR_RUMBLE_LOW            = 0.20  # low-frequency motor strength  (0.0..1.0)
SONAR_RUMBLE_HIGH           = 1.00  # high-frequency motor strength (0.0..1.0)

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
BTN_LOGITECH = 8  # Logitech / Guide button (your mapping)
BTN_LS = 10  # Left stick press (L3) (Logitech F710: your test showed index=10)
BTN_RS    = 9   # Right stick press (R3)
# BTN_GUIDE = 10  # (Optional) Logitech / Guide button if exposed by your OS


# ----- Arm / camera poses (from pf_April_nav_web_drive_store.py) -----
def look_forward():
    Board.setPWMServoPulse(1, 1500, 500)
    Board.setPWMServoPulse(3, 700, 1000)
    Board.setPWMServoPulse(4, 2425, 1000)
    Board.setPWMServoPulse(5, 790, 1000)
    Board.setPWMServoPulse(6, 1500, 1000)
    time.sleep(1)

def look_around():
    Board.setPWMServoPulse(1, 1500, 500)
    Board.setPWMServoPulse(3, 700, 500)
    Board.setPWMServoPulse(4, 2425, 500)
    Board.setPWMServoPulse(5, 790, 500)
    Board.setPWMServoPulse(6, 1500, 500)

    Board.setPWMServoPulse(6,500, 200)
    time.sleep(.2)
    Board.setPWMServoPulse(6, 2500, 2000)
    time.sleep(2)    
    say_no()


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
    Board.setPWMServoPulse(3, 900, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(3, 500, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(3, 900, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(3, 500, 200)
    time.sleep(0.2)
    Board.setPWMServoPulse(3, 700, 200)


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
    Board.setPWMServoPulse(3, 2400, 2000)
    Board.setPWMServoPulse(4, 700, 2000)
    Board.setPWMServoPulse(5, 1700, 2000)
    time.sleep(2)
    Board.setPWMServoPulse(1, 2020, 2000)
    time.sleep(2.1)
    look_forward()



# ----- Sonar + LED helpers -----
def _robot_led_set(color):
    """Set the robot's on-board RGB LEDs (best-effort).

    Your Board RGB examples set pixels 0 and 1 together, so we do the same when possible.
    """
    try:
        # Common Hiwonder Board API: Board.RGB.setPixelColor + Board.RGB.show()
        if hasattr(Board, "RGB") and hasattr(Board.RGB, "setPixelColor"):
            try:
                Board.RGB.setPixelColor(0, color)
                Board.RGB.setPixelColor(1, color)
            except Exception:
                # Some firmwares expose only one pixel
                Board.RGB.setPixelColor(0, color)
            Board.RGB.show()
            return

        # Fallbacks (some firmwares expose these directly)
        if hasattr(Board, "setPixelColor"):
            try:
                Board.setPixelColor(0, color)
                Board.setPixelColor(1, color)
            except Exception:
                Board.setPixelColor(0, color)

            if hasattr(Board, "show"):
                Board.show()

    except Exception as e:
        # DonÃ¢â‚¬â„¢t let LED issues break driving
        print(f"[WARN] Robot LED update failed: {e}")


def _buzzer_set(on: bool) -> bool:
    """Best-effort robot buzzer control. Returns True if it succeeded."""
    try:
        # Common Hiwonder Board API:
        #   Board.setBuzzer(1) / Board.setBuzzer(0)
        if hasattr(Board, "setBuzzer") and callable(getattr(Board, "setBuzzer")):
            Board.setBuzzer(1 if on else 0)
            return True

        # Other possible naming variants (keep safe / best-effort)
        for name in ("set_buzzer", "buzzer", "setBuzzerState"):
            if hasattr(Board, name) and callable(getattr(Board, name)):
                getattr(Board, name)(1 if on else 0)
                return True
    except Exception:
        return False
    return False


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



def _sonar_led_solid(sonar, r: int, g: int, b: int):
    """Set both sonar LEDs to a solid color."""
    try:
        c = Board.PixelColor(int(r), int(g), int(b))
        sonar.setPixelColor(0, c)
        sonar.setPixelColor(1, c)
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

    # Sonar alert helpers (flash + rumble when very close)
    last_dist_mm = None
    last_rumble_time = 0.0
    last_critical_rumble_time = 0.0
    critical_mode = False
    last_flash_time = 0.0
    flash_on = True
    rumble_supported = hasattr(js, "rumble") and callable(getattr(js, "rumble", None))
    last_sonar_check = 0.0
    last_sonar_rand  = 0.0

    # Buzzer (beeps) state (best-effort; depends on firmware exposing Board.setBuzzer)
    buzzer_supported = True  # we will detect support on first use
    buzzer_on = False
    buzzer_off_time = 0.0
    last_beep_time = 0.0
    last_critical_beep_time = 0.0

    try:
        while running:
            # Process events (needed for pygame to update joystick state)
            for event in pygame.event.get():
                if event.type == pygame.JOYBUTTONDOWN:
                    if js.get_button(BTN_A):
                        print("[A] Look forward pose")
                        look_forward()

                    if js.get_button(BTN_B):
                        print("[B] Look sad pose")
                        look_sad()
                        

                    if js.get_button(BTN_Y):
                        print("[Y] say yes sequence")
                        say_yes()

                    if js.get_button(BTN_X):
                        print("[X] say no sequence")
                        say_no()

                    if js.get_button(BTN_BACK):
                        print("[Back] STOP")
                        bot.reset_motors()

                    if js.get_button(BTN_START):
                        print("[Start] Quit requested")
                        #running = False


                    if js.get_button(BTN_LOGITECH):
                        print("[Logitech] Look around sequence")
                        look_around()

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
                            last_dist_mm = None
                            last_rumble_time = 0.0
                            last_critical_rumble_time = 0.0
                            critical_mode = False
                            last_flash_time = 0.0
                            flash_on = True
                            print("[R3] Sonar display ON")

                    if js.get_button(BTN_LS):
                        sonar_enabled = False
                        last_dist_mm = None
                        # Turn off buzzer immediately
                        _buzzer_set(False)
                        buzzer_on = False
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

                # Turn off buzzer if a beep pulse has elapsed (non-blocking)
                if buzzer_on and now >= buzzer_off_time:
                    if _buzzer_set(False):
                        buzzer_on = False

                # Read distance (throttled)
                distance_updated = False
                if (now - last_sonar_check) >= SONAR_CHECK_INTERVAL_SEC:
                    last_sonar_check = now
                    try:
                        dist_mm = sonar.getDistance()
                    except Exception as e:
                        print(f"[WARN] Sonar read failed: {e}")
                        sonar_enabled = False
                        last_dist_mm = None
                        _sonar_led_off(sonar)
                        _robot_led_set(Board.PixelColor(0, 0, 0))
                    else:
                        last_dist_mm = dist_mm
                        distance_updated = True

                # Robot LED feedback + controller rumble when REALLY close
                if last_dist_mm is not None:
                    try:
                        d = float(last_dist_mm)
                    except Exception:
                        d = None

                    if d is not None and d <= SONAR_CRITICAL_THRESHOLD_MM:
                        # ---- CRITICAL zone (<= 4 inches): fast flash + strong rumble + sonar LEDs red ----
                        if not critical_mode:
                            critical_mode = True
                            _sonar_led_solid(sonar, 255, 0, 0)   # sonar LEDs solid red
                            flash_on = True

                        # Fast flash red / off
                        if (now - last_flash_time) >= SONAR_CRITICAL_FLASH_INTERVAL_SEC:
                            last_flash_time = now
                            flash_on = not flash_on

                        if flash_on:
                            _robot_led_set(Board.PixelColor(255, 0, 0))
                        else:
                            _robot_led_set(Board.PixelColor(0, 0, 0))

                        # Strong rumble pulse (cooldown) if supported
                        if rumble_supported and (now - last_critical_rumble_time) >= SONAR_CRITICAL_RUMBLE_COOLDOWN_SEC:
                            try:
                                js.rumble(SONAR_CRITICAL_RUMBLE_LOW, SONAR_CRITICAL_RUMBLE_HIGH, SONAR_CRITICAL_RUMBLE_DURATION_MS)
                            except Exception:
                                rumble_supported = False
                            last_critical_rumble_time = now
                        # Rapid beeps (critical <= 4 in)
                        if buzzer_supported and (now - last_critical_beep_time) >= SONAR_CRITICAL_BEEP_INTERVAL_SEC:
                            if _buzzer_set(True):
                                buzzer_on = True
                                buzzer_off_time = now + SONAR_CRITICAL_BEEP_DURATION_SEC
                            else:
                                buzzer_supported = False
                            last_critical_beep_time = now

                    elif d is not None and d < SONAR_DISTANCE_THRESHOLD_MM:
                        # ---- TOO CLOSE zone (< ~1 ft): soft rumble + normal flash ----
                        if critical_mode:
                            # Leaving critical zone Ã¢â€ â€™ go back to random sonar colors immediately
                            critical_mode = False
                            _sonar_led_randomize(sonar)
                            last_sonar_rand = now

                        # Flash red / off (slower than critical)
                        if (now - last_flash_time) >= SONAR_FLASH_INTERVAL_SEC:
                            last_flash_time = now
                            flash_on = not flash_on

                        if flash_on:
                            _robot_led_set(Board.PixelColor(255, 0, 0))
                        else:
                            _robot_led_set(Board.PixelColor(0, 0, 0))

                        # Soft rumble pulse (cooldown) if supported
                        if rumble_supported and (now - last_rumble_time) >= SONAR_RUMBLE_COOLDOWN_SEC:
                            try:
                                js.rumble(SONAR_RUMBLE_LOW, SONAR_RUMBLE_HIGH, SONAR_RUMBLE_DURATION_MS)
                            except Exception:
                                rumble_supported = False
                            last_rumble_time = now
                        # Short beep (<= 1 ft)
                        if buzzer_supported and (now - last_beep_time) >= SONAR_BEEP_COOLDOWN_SEC:
                            if _buzzer_set(True):
                                buzzer_on = True
                                buzzer_off_time = now + SONAR_BEEP_DURATION_SEC
                            else:
                                buzzer_supported = False
                            last_beep_time = now

                    else:
                        # Not in the "too close" zone Ã¢â€ â€™ steady LED based on distance
                        if critical_mode:
                            # Leaving critical zone Ã¢â€ â€™ go back to random sonar colors immediately
                            critical_mode = False
                            _sonar_led_randomize(sonar)
                            last_sonar_rand = now

                        flash_on = True
                        if distance_updated:
                            _robot_led_from_distance(last_dist_mm)

                # Randomize the *sonar* LEDs for fun / visibility
                if (not critical_mode) and ((now - last_sonar_rand) >= SONAR_RANDOM_COLOR_SEC):
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

        # Ensure buzzer is off
        try:
            _buzzer_set(False)
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
          "A = look_forward, B = look_sad, Logitech = look_around, "
          "D-pad = arm actions, R3 = sonar ON, L3 = sonar OFF, Back = STOP, Start = quit.")
    drive_loop(bot, js)


if __name__ == "__main__":
    main()
