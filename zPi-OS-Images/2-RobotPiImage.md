# **2 Robot Pi Image**

1. **Create a fresh Raspberry Pi OS**
  Use Raspberry Pi Imager to create a fresh Raspberry Pi OS (64-bit) SD card
   - https://www.raspberrypi.com/software/
   - current imager version 1.9.4
   - current Pi OS Released: 2025-05-13
  
1. **Boot the Raspberry Pi with the new card**
   
   Follow the wizard to configure the image

1. **Enable interface:** ssh, vnc and i2c
   
    You can use GUI - Pi/Preferences/Raspberry Pi Configuration - or CLI use the command beow
    ~~~
    sudo raspi-config
    ~~~
    Optional - change Hostname: raspi-config / 1. system options / S4 Hostname 

1. **Update OS to current patch level**

    ~~~
    sudo apt-get update && sudo apt-get upgrade -y
    ~~~
    
1. **Remove installed packages that are no longer required** If needed

    ~~~
    sudo apt autoremove -y
    ~~~
    
1. **Remove update block**

    ~~~
    sudo rm /usr/lib/python3.11/EXTERNALLY-MANAGED
    ~~~

    
1. **Install tensorflow lite and OpenVC**

    ~~~
    sudo python3 -m pip install --upgrade pip
    sudo pip install opencv-python opencv-contrib-python
    ~~~

1. **View OpenCV version that was installed (4.10.0)**

    ~~~
    sudo python3 -c "import cv2; print(cv2.__version__)"
    ~~~
    OpenCV version = 4.11.0

1. **Intall April Tag library**

    ~~~
    sudo pip install pupil-apriltags
    ~~~


1. **(Optional)Install Juptyer Notebook**

    ~~~
    sudo pip3 install jupyter
    ~~~

1. **Additional libraries needed**

    ~~~
    sudo pip install PyYAML
    sudo pip install rpi_ws281x
    sudo pip install json-rpc
    sudo pip install matplotlib
    sudo pip install pandas
    sudo apt-get install python3-pyqt5.qtsql
    ~~~

1. **Visual Studio Code***

    - from the pi menu, select Preferences/Recomended Software
    - scroll down and check Visual Studio Code
    - Click Apply


1. **Add MasterPi and MasterPi_PC_Software folder to /home/pi/**
   
   NOTE: If a username other than pi is used, you will need to create a /home/pi folder to store the MasterPi code.
   
   Example: user name = robot
   ~~~
   sudo mkdir /home/pi
   sudo chown robot:robot /home/pi
   sudo chmod 755 /home/pi
   ~~~


1. **Add AutonomousEdgeRobotics folder to /home/pi/Desktop/**


