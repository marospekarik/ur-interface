
This is fork of https://github.com/Mandelbr0t/UniversalRobot-Realtime-Control, https://bitbucket.org/RopeRobotics/ur-interface/src

This repo extend the UR capabilities to mimick real-time drawing using XY coordinate input from WACOM tablet or any other desirable XY input source. Pixel translation to robot coordinate system is taken from the previous research project: https://github.com/robodave94/ur10DrawingSocial


# Installation
Tested on Python 3.7 and 3.9

pip3 install opencv-python PyQt5 scipy numpy paho-mqtt six
# Run
1. In App.py change host IP to your robot/simulator IP address.

# Todo:
1. ~~Add install script~~
