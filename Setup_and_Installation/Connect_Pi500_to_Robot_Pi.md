# **Connect Pi500 to Robot Pi and test**

## Prerequisites:

1. Robot is on and you have the robot's current IP (shown below as XXX.XXX.XXX.XXX)
1. Pi500 is connected to monitor, mouse and powered on

## Steps: from the Raspberry Pi 500

1. **SSH Connection**

    Open a terminal and enter the following command replacing the XXX.XXX.XXX.XXX with the robot's IP
    - NOTE: Username = robot. default Password was R4spb3rry
      
    ~~~
    ssh robot@XXX.XXX.XXX.XXX
    ~~~

1. **Run [pf_start_robot.py](/code/pf_start_robot.py)**
  
   This script initualizes the robot and sets the arm to starting position
   
   ~~~
   cd /home/robot/code
   sudo python pf_start_robot.py
   ~~~

1. **Run [pf_test_arm_servos.py](/code/pf_test_arm_servos.py)**

   The following script will move each servo a little starting with the claw. Check to make sure all servos are plugged into the correct location.

    ~~~
    cd /home/robot/code
    sudo python pf_test_arm_servos.py
    ~~~

1. **Run [pf_test_motors.py](/code/pf_test_motors.py)**

   The following script will move each motor to test that the motors are plugged into the correct location. The wheels will run in the following order:
   
   - left front
   - right front
   - left back
   - right back  

    ~~~
    cd /home/robot/code
    sudo python pf_test_motors.py
    ~~~

1. **Run [pf_test_drive_movements.py](/code/pf_test_drive_movements.py)**

   Please place the robot on the floor before continuing. The following script will test robot movements and demonstrate the mecanum wheels. The robot will move in the following order:
   
   - Forward
   - Reverse
   - StrafeRight
   - StrafeLeft
   - TurnRight
   - TurnLeft

    ~~~
    cd /home/robot/code
    sudo python pf_test_drive_movements.py
    ~~~

1. **Run [pf_test_arm_pickup_movements.py](/code/pf_test_arm_pickup_movements.py)**

   Please place the robot on the floor and set a block in front of the robot. The following script will demonstrate the arm picking up a block and loading it onto its back. 

    ~~~
    cd /home/robot/code
    sudo python pf_test_arm_pickup_movements.py
    ~~~

# **Remote connect to the Robot Pi if needed**


1. **VNC Connection**

    Launch RealVNC Viewer
   
     <img src="/zzimages/RealVNCViewer.jpg" width="200" > 

     <img src="/zzimages/VNC.jpg" width="200" > 

     <img src="/zzimages/VNC1.jpg" width="200" > 

     <img src="/zzimages/VNC2.jpg" width="200" > 

    Input the robots IP XXX.XXX.XXX.XXX to connect. Username = robot. default Password was R4spb3rry

1. **Run Camera test within the VNC viewer**
 
    If picture is black, then remove the lens cap
   
    If the picture is out of focus, turn the camea lense left or right to focus.
   
    ~~~
    cd /home/robot/code
    sudo python Camera.py
    ~~~

1. **Calibrate servos within the VNC viewer**
  
    Calibrate may be needed based on the start up position of the robot arm in step 2 above. Normal start up position for the arm should look like the picture below.
   
   <img src="/zzimages/ArmStartUp.jpeg" width="200" > 

    If the start up position is not the same, the servo positions will need to be corrected or a servo may need to be replaced. The Arm.py program is a way to interact with the arm and can help you fuigure out what is needed.

    ~~~
    python /home/pi/MasterPi_PC_Software/Arm.py
    ~~~
  
[Return to main workshop page](/README.md)





