# Robot Capabilities

## Basic Features

1. **[Simple Drive Guide](Simple_Drive_Guide.md)**

1. **[Simple Arm Movements Guide](Simple_Arm_Movements_Guide.md)**
  
1. **[Sonar Guide](Sonar_Guide.md)**

1. **[Buzzer and RGB Guide](Buzzer_and_RGB_Guide.md)**

## Camera - these require VNC connetions to see the camera feed. 

1. **VNC Connection**

    Launch RealVNC Viewer
   
     <img src="/zzimages/RealVNCViewer.jpg" width="200" > 

     <img src="/zzimages/VNC.jpg" width="200" > 

     <img src="/zzimages/VNC1.jpg" width="200" > 

     <img src="/zzimages/VNC2.jpg" width="200" > 

    Input the robots IP XXX.XXX.XXX.XXX to connect

    1. **Run camera scripts**
  
       Open a terminal and enter the following command.  
       ~~~
       cd /home/robot/code
       sudo python Camera.py
       ~~~
    1. to stop the script in the terminal , hit ctrl-c. then run the pf_AprilCamera.py 
       
       ~~~
       cd /home/robot/code
       sudo python pf_AprilCamera.py
       ~~~

      See the links below for more details on these two scripts. 
   
1. **[Camera Guide](Camera_Guide.md)**

1. **[April Tags with Camera](AprilTag_Camera_Guide.md)**
