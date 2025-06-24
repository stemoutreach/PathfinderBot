# **2 Robot Setup**

<img src="https://github.com/stemoutreach/AutonomousEdgeRobotics/blob/main/GettingStarted/zzimages/IMG_2048.jpg" width="400" > 

## Prerequisites:

1. Robot is assembled
1. Batteries are charged and installed
1. Robot Pi is connected to monitor and keyboard

## Steps:

1. **Turn on Robot**

   There are two switches. One on the motor controller and one on the battery container.
   
   <img src="https://github.com/stemoutreach/AutonomousEdgeRobotics/blob/main/zzimages/RoobotOnOff.jpg" width="400" > 

   
1. **change defaul password and hostname**

    Open the Configuation tool at **Pi -> Preferences -> Raspberry Pi Configuation** and follow instructions. Make the hostname unique. Maybe use your team name or initials and add robot if you use the same hostname as the desktop pi. 
   
   <img src="https://github.com/stemoutreach/AutonomousEdgeRobotics/blob/main/zzimages/PiConfigPWandHost.jpg" width="500" > 


1. **Connect to WiFi**

   Check the network icon top right of the Taskbar. If the network icon looks like the image below, click icon and select the correct network to connect to. 

   <img src="https://github.com/stemoutreach/AutonomousEdgeRobotics/blob/main/zzimages/wifisetup-01.jpg" width="200" > 

1. **Get the assigned IP for the robot**

Hover the mouse cursor ver the active WiFi icon and copy the assigned IP address. This IP will be used to connect the Pi500 to the robot.   

1. **Run start up script**
  
   Open a terminal and enter the following command. (This script initualizes the robot and sets the arm to starting position) 
   ~~~
   sudo python StartUp.py
   ~~~

1. **Run servo test**

   The following script will move each servo a little starting with the claw. Check to make sure all servos are plugged into the correct location. The wheels will also run in order:
   - left front
   - right front
   - left back
   - right back  

    ~~~
    sudo python /home/pi/MasterPi/HiwonderSDK/Servo_test.py
    ~~~

1. **Run Camera test**

    NOTE: monitor must be connected to the robot to view the camera window.
    
    If picture is black, then remove the lens cap
   
    If the picture is out of focus, turn the camea lense left or right to focus.
   
    ~~~
    sudo python CameraTest.py
    ~~~

1. **Calibrate servos**
  
    Calibrate may be needed based on the start up position of the robot arm in step 2 above. Normal start up position for the arm should look like the picture below.
   
   <img src="https://github.com/stemoutreach/AutonomousEdgeRobotics/blob/main/zzimages/ArmStartUp.jpeg" width="200" > 

    If the start up position is not the same, the servo positions will need to be corrected or a servo may need to be replaced. The Arm.py program is a way to interact with the arm and can help you fuigure out what is needed.

    ~~~
    python MasterPi_PC_Software/Arm.py
    ~~~

    


    
