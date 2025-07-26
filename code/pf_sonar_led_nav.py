import time
from mecanum import MecanumChassis
from Sonar import Sonar
import Board

# Constants
DISTANCE_THRESHOLD_MM = 305  # 1 foot in mm
CAUTION_THRESHOLD_MM = 610   # 2 feet in mm
TURN_SPEED = 40
FORWARD_SPEED = 50
CHECK_DELAY = 0.1
DEMO_DURATION = 15           # seconds

# Initialize
chassis = MecanumChassis()
sonar = Sonar()

def drive_forward():
    chassis.translation(0, FORWARD_SPEED)

def stop():
    chassis.reset_motors()

def turn_left(duration=1.0):
    chassis.set_velocity(0, 0, -TURN_SPEED)
    time.sleep(duration)
    stop()

def turn_right(duration=1.0):
    chassis.set_velocity(0, 0, TURN_SPEED)
    time.sleep(duration)
    stop()

def update_led(distance):
    if distance >= CAUTION_THRESHOLD_MM:
        color = Board.PixelColor(0, 255, 0)  # Green
    elif distance >= DISTANCE_THRESHOLD_MM:
        color = Board.PixelColor(255, 255, 0)  # Yellow
    else:
        color = Board.PixelColor(255, 0, 0)  # Red

    sonar.setPixelColor(0, color)
    sonar.setPixelColor(1, color)
    sonar.show()

def blink_red():
    red = Board.PixelColor(255, 0, 0)
    off = Board.PixelColor(0, 0, 0)
    sonar.setPixelColor(0, red)
    sonar.setPixelColor(1, red)
    sonar.show()
    time.sleep(0.3)
    sonar.setPixelColor(0, off)
    sonar.setPixelColor(1, off)
    sonar.show()
    time.sleep(0.7)

def is_path_clear():
    distance = sonar.getDistance()
    print(f"Distance: {distance} mm")
    update_led(distance)
    return distance > DISTANCE_THRESHOLD_MM

def main():
    print("Starting navigation...")
    sonar.setRGBMode(0)  # Static LED mode
    start_time = time.time()
    last_printed = DEMO_DURATION

    try:
        while True:
            elapsed = time.time() - start_time
            remaining = int(DEMO_DURATION - elapsed)

            if remaining <= 0:
                print("Demo time ended. Stopping robot.")
                break

            # Countdown feedback
            if remaining <= 10:
                print(f"⏳ Ending in {remaining} seconds...")
                blink_red()
            elif remaining % 5 == 0 and remaining != last_printed:
                print(f"Time remaining: {remaining} seconds")
                last_printed = remaining

            drive_forward()
            while is_path_clear():
                elapsed = time.time() - start_time
                remaining = int(DEMO_DURATION - elapsed)

                if remaining <= 0:
                    print("Demo time ended during drive. Stopping robot.")
                    break
                elif remaining <= 10:
                    print(f"⏳ Ending in {remaining} seconds...")
                    blink_red()
                elif remaining % 5 == 0 and remaining != last_printed:
                    print(f"Time remaining: {remaining} seconds")
                    last_printed = remaining

                time.sleep(CHECK_DELAY)

            stop()
            if remaining <= 0:
                break

            print("Obstacle detected. Stopping.")
            time.sleep(0.2)

            print("Turning left .5s...")
            turn_left(0.5)
            if is_path_clear():
                continue

            print("Turning right 1s...")
            turn_right(1)
            if is_path_clear():
                continue

            print("Turning right .5s...")
            turn_right(0.5)
            if is_path_clear():
                continue

            print("Blocked. Ending program.")
            break

    finally:
        stop()
        sonar.setPixelColor(0, Board.PixelColor(0, 0, 0))
        sonar.setPixelColor(1, Board.PixelColor(0, 0, 0))
        sonar.show()

if __name__ == "__main__":
    main()
