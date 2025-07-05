

# Software Dependencies

The following software packages and libraries are required for the **PathfinderBot** to function properly. These dependencies support camera vision, tag detection, data analysis, visualization, and robot control on the Raspberry Pi.

## 📷 Computer Vision & Tag Detection

### `opencv-python` (Version: 4.11.0)
OpenCV is an open-source computer vision library used to process images and video streams. In PathfinderBot, it's used to capture video from the camera, detect objects, and work with AprilTags for navigation.

### `pupil-apriltags`
A Python library for detecting AprilTags — a type of visual fiducial marker. It allows the robot to recognize and estimate the position of tags in the environment for localization and navigation.

## 💻 Programming & Development Tools

### `jupyter`
Jupyter provides an interactive coding environment through notebooks. It’s useful for developing and testing Python code in a step-by-step manner with immediate visual feedback.

### `PyYAML`
PyYAML is a YAML parser and emitter for Python. It's used to read and write configuration files in a human-readable format.

## 🔧 Hardware Control

### `rpi_ws281x`
A Raspberry Pi library for controlling WS281x-based LED strips (e.g., NeoPixels). It may be used to give the PathfinderBot visual feedback using LED lighting.

## 🔌 Communication & APIs

### `json-rpc`
A lightweight remote procedure call (RPC) protocol encoded in JSON. This allows components of the robot (e.g., web interface and control scripts) to communicate efficiently over a local or networked connection.

## 📊 Data Analysis & Visualization

### `matplotlib`
A plotting library used to create static, animated, and interactive visualizations in Python. It helps visualize data such as AprilTag detection results or sensor values.

### `pandas`
Pandas is a powerful data manipulation and analysis library. It’s used to structure and analyze tabular data, logs, or experimental results from the robot.

## 🧱 GUI and SQL Integration

### `python3-pyqt5.qtsql`
This provides SQL database support through PyQt5. It can be used for applications where PathfinderBot logs or retrieves data from a local SQLite database in a GUI environment.

## 🛠️ Code Editing & Debugging

### `Visual Studio Code`
VS Code is a lightweight, extensible code editor that supports Python and remote development on Raspberry Pi. It’s the recommended IDE for editing, debugging, and managing the PathfinderBot project files.

## 🛠️ MasterPi
software provided by MasterPI robot

# Build Raspberry Pi OS image for Pi 500 and Robot Pi

Steps to create the OS images
## [1 Pi 500 Build Steps](OS_Image/Pi500_Build_Steps.md)
## [2 Robot Pi Build Steps](OS_Image/Robot_Pi_Build_Steps.md)

[Return to Setup and Installation Page](README.md)
