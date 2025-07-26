import time
from mecanum import MecanumChassis
from Sonar import Sonar
import Board

# Constants
DISTANCE_THRESHOLD_MM = 305  # 1 foot in mm
CAUTION_THRESHOLD_MM = 610   # 2 feet in mm
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

def is_path_clear():
    distance = sonar.getDistance()
    print(f"Distance: {distance} mm")
    update_led(distance)
    return distance > DISTANCE_THRESHOLD_MM

def main():
    print("Starting navigation...")
    start_time = time.time()
    sonar.setRGBMode(0)  # Static color mode

    try:
        while True:
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
