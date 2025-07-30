#!/usr/bin/env python

import time
from pf_AprilCamera import Camera, TAG_TABLE
from pf_AprilTagNavigator import AprilTagNavigator
from mecanum import MecanumChassis as Mecanum
import Board

# Initialize components
cam = Camera(resolution=(640, 480))
cam.camera_open()
nav = AprilTagNavigator(cam)
bot = Mecanum()

# Movement actions for TAG_TABLE commands
def turn_left():
    bot.set_velocity(0, 0, -30)
    time.sleep(1.0)
    bot.reset_motors()

def turn_right():
    bot.set_velocity(0, 0, 30)
    time.sleep(1.0)
    bot.reset_motors()

def strafe_left():
    bot.translation(-40, 0)
    time.sleep(1.0)
    bot.reset_motors()

def strafe_right():
    bot.translation(40, 0)
    time.sleep(1.0)
    bot.reset_motors()

def backward_turn_left():
    bot.translation(0, -40)
    time.sleep(1.0)
    turn_left()

def backward_turn_right():
    bot.translation(0, -40)
    time.sleep(1.0)
    turn_right()

def turn_around_strafe_right():
    turn_right()
    turn_right()
    strafe_right()

def turn_around_strafe_left():
    turn_left()
    turn_left()
    strafe_left()

# Map TAG_TABLE commands to actions
ACTION_MAP = {
    "TURN_LEFT": turn_left,
    "TURN_RIGHT": turn_right,
    "STRAFE_LEFT": strafe_left,
    "STRAFE_RIGHT": strafe_right,
    "BACKWARD_TURN_LEFT": backward_turn_left,
    "BACKWARD_TURN_RIGHT": backward_turn_right,
    "TURN_AROUND_STRAFE_RIGHT": turn_around_strafe_right,
    "TURN_AROUND_STRAFE_LEFT": turn_around_strafe_left,
}

# Execute action based on current tag
def execute_tag_action(tag_id):
    action_name = TAG_TABLE.get(tag_id)
    action_func = ACTION_MAP.get(action_name)
    if action_func:
        print(f"Executing action: {action_name}")
        action_func()
    elif action_name == "FINISH":
        print("Reached FINISH tag.")
    else:
        print(f"No defined action for tag ID: {tag_id}")

# Main functionality to continue navigation after Pickup

def continue_nav():
    frame = cam.frame
    if frame is None:
        print("No camera frame available.")
        return

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    tags = cam.detector.detect(gray, estimate_tag_pose=True,
                               camera_params=(cam.mtx[0,0], cam.mtx[1,1], cam.mtx[0,2], cam.mtx[1,2]), tag_size=0.045)

    if tags:
        tag = min(tags, key=lambda t: t.pose_t[2])
        execute_tag_action(tag.tag_id)
    else:
        print("No AprilTag detected to continue navigation.")

# Example scenario
if __name__ == "__main__":
    print("Starting navigation...")
    nav.start()
    while nav.is_running():
        time.sleep(0.1)

    print("Navigation stopped at tag.")

    # Perform pickup
    print("Performing pickup and storage...")
    # Assume PickupBlock is already defined elsewhere and imported
    from pf_April_nav_web_drive_store import PickupBlock
    PickupBlock()

    # Continue navigation based on TAG_TABLE
    print("Continuing navigation...")
    continue_nav()

    cam.camera_close()
