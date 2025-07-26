# **Connect Pi500 to Robot Pi and test**

## Prerequisites:

1. Robot is on and you have the robot's current IP (shown below as XXX.XXX.XXX.XXX)
1. Pi500 is connected to monitor, mouse and powered on

## Steps: from the Raspberry Pi 500

1. **SSH Connection**

    Open a terminal and enter the following command replacing the XXX.XXX.XXX.XXX with the robot's IP
       NOTE: user = robot
    ~~~
    ssh robot@XXX.XXX.XXX.XXX
    ~~~

1. **Run [pf_StartRobot.py](/code/pf_StartRobot.py)**
  
   This script initualizes the robot and sets the arm to starting position
   ~~~
   cd /home/robot/code
   sudo python pf_StartRobot.py
   ~~~

1. **Run servo test**

   The following script will move each servo a little starting with the claw. Check to make sure all servos are plugged into the correct location. The wheels will also run in order:
   - left front
   - right front
   - left back
   - right back  

    ~~~
    cd /home/robot/code
    sudo python Servo_test.py
    ~~~

1. **VNC Connection**

    Launch RealVNC Viewer
   
     <img src="/zzimages/RealVNCViewer.jpg" width="200" > 

    Input XXX.XXX.XXX.XXX to connect
   
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


  
