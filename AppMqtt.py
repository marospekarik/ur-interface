import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import QtCore

import json
import time
import scipy.interpolate
import math
import operator
import paho.mqtt.client as mqtt

import URBasic
from MqttClient import MqttClient
from Robot import MyRobot
class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'RoboUI'
        self.left = 10
        self.top = 10
        self.width = 400
        self.height = 140
        self.activated = False

        # Tablet canvas size
        self.tabletW = 2560
        self.tabletH = 1440

        # Tablet
        self.pen_is_down = False
        self.pen_x = 0
        self.pen_y = 0
        self.pen_pressure = 0
        self.text = ""

        self.initUI()
        self.myRobot = MyRobot()
        #self.myRobot = False
        self.drawingActive = False

        self.client = MqttClient(self)
        self.client.stateChanged.connect(self.on_stateChanged)
        self.client.messageSignal.connect(self.on_messageSignal)

        self.client.hostname = "localhost"
        self.client.connectToHost()

    @QtCore.pyqtSlot(int)
    def on_stateChanged(self, state):
        if state == MqttClient.Connected:
            print(state)
            self.client.subscribe("heart/test")

    @QtCore.pyqtSlot(str)
    def on_messageSignal(self, msg):
        try:
            if self.activated:
                val = msg.split(',')
                print("Received value:", val[0], ",", val[1])
                x = int(val[0])
                y = int(val[1])
                coord = self.myRobot.PixelTranslation(x, y, self.tabletH, self.tabletW)
                z = -coord[2]
                self.myRobot.robot.set_realtime_pose([coord[0], coord[1], z, 0,3.14,0])
            else:
                print("not activated")
        except ValueError:
            print("error: Parsing Error")

    def initUI(self):
        self.setWindowTitle(self.title)
        
        # Create a button in the window
        self.button = QPushButton('Calibrate', self)
        self.button.move(20,80)

        self.button2 = QPushButton('Activate', self)
        self.button2.move(100,100)
        
        # connect button to function on_click
        self.button.clicked.connect(self.on_click_calibrate)
        self.button2.clicked.connect(self.on_click_test)

        # Resizing the sample window to full desktop size:
        frame_rect = app.desktop().frameGeometry()
        width, height = frame_rect.width(), frame_rect.height()
        self.resize(width, height)
        self.move(-9, 0)
        self.show()

    @pyqtSlot()
    def on_click_calibrate(self):
        self.myRobot.robot.freedrive_mode()
        QMessageBox.question(self, 'Bottom Left','Press OK to confirm Bottom Left', QMessageBox.Ok, QMessageBox.Ok)
        self.myRobot.Calibrate(0)
        QMessageBox.question(self, 'Top Left','Press OK to confirm Top Left', QMessageBox.Ok, QMessageBox.Ok)
        self.myRobot.Calibrate(1)
        QMessageBox.question(self, 'Top Right','Press Enter to confirm Top Right', QMessageBox.Ok, QMessageBox.Ok)
        self.myRobot.Calibrate(2)
        QMessageBox.question(self, 'Bottom Right','Press Enter to confirm Bottom Right', QMessageBox.Ok, QMessageBox.Ok)
        self.myRobot.Calibrate(3)

    
    @pyqtSlot()
    def on_click_test(self):
        self.myRobot.constructDrawingCanvas()
        self.myRobot.calculateCroppedSizing(self.tabletH, self.tabletW)
        self.activated = True

    def tabletEvent(self, tabletEvent):
        #https://docs.huihoo.com/pyqt/pyqt/html/qtabletevent.html
        self.pen_x = tabletEvent.globalX()
        self.pen_y = tabletEvent.globalY()
        self.pen_pressure = int(tabletEvent.pressure() * 100)
        if tabletEvent.type() == QTabletEvent.TabletPress:
            self.pen_is_down = True
            self.text = "TabletPress event"
        elif tabletEvent.type() == QTabletEvent.TabletMove:
            self.pen_is_down = True
            self.text = "TabletMove event"
        elif tabletEvent.type() == QTabletEvent.TabletRelease:
            self.pen_is_down = False
            self.text = "TabletRelease event"
        self.text += " at x={0}, y={1}, pressure={2}%,".format(self.pen_x, self.pen_y, self.pen_pressure)
        if self.pen_is_down:
            self.text += " Pen is down."
        else:
            self.text += " Pen is up."

        #self.time = int(round(time.time() * 1000))
        #if(self.time - self.prevTime > 20):
        coord = self.myRobot.PixelTranslation(self.pen_x, self.pen_y, self.tabletH, self.tabletW)
        z = -coord[2]
        if self.pen_pressure < 15:
            z = -coord[2] + 0.04
        self.myRobot.robot.set_realtime_pose([coord[0], coord[1], z, 0,3.14,0])

        tabletEvent.accept()
        self.update()
    
    def paintEvent(self, event):
        text = self.text
        i = text.find("\n\n")
        if i >= 0:
            text = text.left(i)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignLeft , text)

    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())