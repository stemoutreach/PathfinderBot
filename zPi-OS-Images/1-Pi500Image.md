# **1 Desktop Pi Image** 

1. **Create a fresh Raspberry Pi OS**
  Use Raspberry Pi Imager to create a fresh Raspberry Pi OS (64-bit) SD card
   - https://www.raspberrypi.com/software/
   - current imager version 1.9.4
   - current Pi OS Released: 2025-05-13
  
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
