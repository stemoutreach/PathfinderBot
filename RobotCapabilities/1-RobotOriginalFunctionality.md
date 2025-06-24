# **1 Robot Original Functionality**

## Prerequisites:

1. Robot is assembled
1. SD card is in the Raspberry Pi on the robot
1. Batteries are charged and installed
1. Robot Pi is connected to monitor and keyboard

## Steps

1. **Robot Arm Interface**

   ~~~
   python MasterPi_PC_Software/Arm.py
   ~~~

   <img src="https://github.com/stemoutreach/AutonomousEdgeRobotics2.0/blob/main/zzimages/ArmAction.png" width="600" >   


1. **Functions**

   The MasterPi.py module needs to be running in the background for the functions modules to work. Open a terminal window and run the MasterPi.py
   ~~~
   sudo python /home/pi/MasterPi/MasterPi.py 
   ~~~

      - Open an additional terminal window to run one function modules. Use ctrl+C to stop the function before starting anohther one

      
        <img src="https://github.com/stemoutreach/AutonomousEdgeRobotics2.0/blob/main/zzimages/Features.png" width="600" >   

         ~~~
         sudo python /home/pi/MasterPi/Functions/ColorDetect.py 
         ~~~

         ~~~
         sudo python /home/pi/MasterPi/Functions/ColorSorting.py 
         ~~~
      
         ~~~
         sudo python /home/pi/MasterPi/Functions/ColorTracking.py 
         ~~~

         ~~~
         sudo python /home/pi/MasterPi/Functions/VisualPatrol.py 
         ~~~

         ~~~
         sudo python /home/pi/MasterPi/Functions/Avoidance.py 
         ~~~
      
         ~~~
         sudo python /home/pi/MasterPi/Functions/Color_Warning.py 
         ~~~

