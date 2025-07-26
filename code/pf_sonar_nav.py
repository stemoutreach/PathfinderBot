import time
from mecanum import MecanumChassis
from Sonar import Sonar

# Constants
DISTANCE_THRESHOLD_MM = 305  # 1 foot in mm
TURN_SPEED = 40              # Adjust speed if needed
FORWARD_SPEED = 50
CHECK_DELAY = 0.1            # Delay between distance checks
DEMO_DURATION = 15           # Demo run time in seconds

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
    start_time = time.time()

    try:
        while True:
            # Check if demo time has expired
            if time.time() - start_time >= DEMO_DURATION:
                print("Demo time ended. Stopping robot.")
                break

            drive_forward()
            while is_path_clear():
                if time.time() - start_time >= DEMO_DURATION:
                    print("Demo time ended during drive. Stopping robot.")
                    break
                time.sleep(CHECK_DELAY)

            stop()
            if time.time() - start_time >= DEMO_DURATION:
                break

            print("Obstacle detected. Stopping.")
            time.sleep(0.2)

            print("Turning left...")
            turn_left(0.5)
            if is_path_clear():
                continue

            print("Turning right 1s...")
            turn_right(1)
            if is_path_clear():
                continue

            print("Turning right 0.5s...")
            turn_right(0.5)
            if is_path_clear():
                continue

            print("Blocked. Ending program.")
            break

    finally:
        stop()

if __name__ == "__main__":
    main()
