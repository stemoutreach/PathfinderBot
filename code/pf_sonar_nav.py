import time
from mecanum import MecanumChassis
from Sonar import Sonar

# Constants
DISTANCE_THRESHOLD_MM = 305  # 1 foot in mm
TURN_SPEED = 40              # Adjust speed if needed
FORWARD_SPEED = 50
CHECK_DELAY = 0.1            # Delay between distance checks

# Initialize robot
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

def is_path_clear():
    distance = sonar.getDistance()
    print(f"Distance: {distance} mm")
    return distance > DISTANCE_THRESHOLD_MM

def main():
    print("Starting navigation...")
    try:
        while True:
            drive_forward()
            while is_path_clear():
                time.sleep(CHECK_DELAY)

            print("Obstacle detected. Stopping.")
            stop()
            time.sleep(0.2)

            # Try resolving obstacle
            print("Turning left...")
            turn_left(.5)
            if is_path_clear():
                continue

            print("Turning right 2s...")
            turn_right(1)
            if is_path_clear():
                continue

            print("Turning right 1s...")
            turn_right(.5)
            if is_path_clear():
                continue

            print("Blocked. Ending program.")
            break

    finally:
        stop()

if __name__ == "__main__":
    main()
