# **Pi500 OS Build Steps** 

1. **Create a fresh Raspberry Pi OS**
  Use Raspberry Pi Imager to create a fresh Raspberry Pi OS (64-bit) SD card
   - https://www.raspberrypi.com/software/
   - current imager version 2.0.0
   - current Pi OS Released: 2025-10-01
   - Last tested 2025-11-24
  
1. **Boot the Raspberry Pi with the new card**

1. **Suggest changing defaul password for pi**
   
1. **Suggest changing Hostname for pi** 

1. **Update OS to current patch level**

    ~~~
    sudo apt-get update && sudo apt-get upgrade -y
    ~~~
    
1. **Remove installed packages that are no longer required**

    ~~~
    sudo apt autoremove -y
    ~~~

1. **Install VNC Viewer and Visual Studio Code**

    - from the pi menu, select Preferences/Recomended Software
    - scroll down and check Visual Studio Code and VNC Viewer
    - Click Apply

1. **Open Visual Studio Code and add extentions**

    - Python
    - Remote ssh
    - Cline
    - jupyter 


