import sys
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import json
import time
import scipy.interpolate
import math
import operator

import URBasic
from MqttClient import MqttClient
from Robot import MyRobot

class WindowDraw(QWidget):
    """
    This "window" is a QWidget. If it has no parent,
    it will appear as a free-floating window.
    """

    def __init__(self, mainWindow):
        super().__init__()
        # Tablet
        self.pen_is_down = False
        self.pen_x = 0
        self.pen_y = 0
        self.pen_pressure = 0
        self.text = ""
        layout = QVBoxLayout()
        # Resizing the sample window to full desktop size:
        frame_rect = app.desktop().frameGeometry()
        width, height = frame_rect.width(), frame_rect.height()
        self.resize(width, height)
        self.move(-9, 0)
        self.setLayout(layout)
        self.mainWindow = mainWindow

    def tabletEvent(self, tabletEvent):
        #https://docs.huihoo.com/pyqt/pyqt/html/qtabletevent.html
        if self.mainWindow.activated:
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
            
            #self.mainWindow.tabletPos = f"X: {self.pen_x} | Y: {self.pen_y}"
            coord = self.mainWindow.myRobot.PixelTranslation(self.pen_x, self.pen_y, self.canvasH, self.canvasW)
            z = -coord[2]
            if self.pen_pressure < 15:
                z = -coord[2] + 0.04
            self.mainWindow.myRobot.robot.set_realtime_pose([coord[0], coord[1], z, 0,3.14,0])
        else: 
            print("not activated")

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

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'RoboUI'
        self.wWidth = 500
        self.wHeight = 300

        self.settings = QSettings("RoboApp", "App")
        self.window_draw = WindowDraw(self)

        # Canvas size
        self.canvasW = self.settings.value("width") #2560
        self.canvasH = self.settings.value("height") #1440
        self.zOffset = float(self.settings.value("zOffset")) or 0 #0.04
        self.remotePos = "X: not received | Y: not received"
        self.tabletPos = "X: not received | Y: not received"
        self.controlMode = self.settings.value("controlMode")

        self.initUI()
        #self.myRobot = MyRobot(host = '169.254.178.76')
        self.myRobot = MyRobot(host = '172.24.210.100')

        #self.myRobot = False
        self.activated = False
        self.freeModeOn = False

        self.client = MqttClient(self)
        self.client.stateChanged.connect(self.on_stateChanged)
        self.client.messageSignal.connect(self.on_messageSignal)
        self.client.hostname = "localhost" #"172.24.210.63"
        self.client.connectToHost()
    
    # def initMqtt():
        # self.client.disconnectFromHost()
        # self.client.hostname = "172.24.210.63"
        # self.client.connectToHost()

    def initUI(self):
        self.setWindowTitle(self.title)
        self.mainLayout = QGridLayout()
        self.setFixedSize(self.wWidth, self.wHeight)
        self.leftLayout = QVBoxLayout()
        self.rightLayout = QGridLayout()

        # Buttons
        #buttons = ["calib", "activate", "canvas", "zOffset", "freeMode", "reset"]
        self.btn_calib = QPushButton('Calibrate', self)
        self.btn_calib.setGeometry(QRect(10, 10, 200, 30))

        self.btn_activate = QPushButton('Activate', self)
        self.btn_activate.setGeometry(QRect(10, 10, 200, 30))
        self.btn_activate.setCheckable(True)

        self.btn_canvas = QPushButton('Set Canvas Size', self)
        self.btn_canvas.setGeometry(QRect(10, 10, 200, 30))

        self.btn_zOffset = QPushButton('Set Z offset', self)
        self.btn_zOffset.setGeometry(QRect(10, 10, 200, 30))
        
        self.btn_freeMode = QPushButton('Free mode', self)
        self.btn_freeMode.setGeometry(QRect(10, 10, 200, 30))
        self.btn_freeMode.setCheckable(True) 

        self.btn_resetErr = QPushButton('Reset error', self)
        self.btn_resetErr.setGeometry(QRect(10, 10, 200, 30))

        self.btn_draw = QPushButton('Draw', self)
        self.btn_draw.setGeometry(QRect(10, 10, 200, 30))

        self.leftLayout.addWidget(self.btn_activate)
        self.leftLayout.addWidget(self.btn_calib)
        self.leftLayout.addWidget(self.btn_canvas)
        self.leftLayout.addWidget(self.btn_zOffset)
        self.leftLayout.addWidget(self.btn_freeMode)
        self.leftLayout.addWidget(self.btn_resetErr)
        self.leftLayout.addWidget(self.btn_draw)

        # connect button to function on_click
        self.btn_calib.clicked.connect(self.on_click_calibrate)
        self.btn_activate.clicked.connect(self.on_click_activate)
        self.btn_canvas.clicked.connect(self.on_click_canvas_size)
        self.btn_zOffset.clicked.connect(self.on_click_z_offset)
        self.btn_freeMode.clicked.connect(self.on_click_free)
        self.btn_resetErr.clicked.connect(self.on_click_reset_error)
        self.btn_draw.clicked.connect(self.on_click_draw)

        #Display text
        self.label_w = QLabel("Width:")
        self.label_w_val = QLabel(str(self.canvasW))
        self.label_h = QLabel('Height:')
        self.label_h_val = QLabel(str(self.canvasH))
        self.label_z = QLabel('Z Offset:')
        self.label_z_val = QLabel(str(self.zOffset))
        self.label_remote_pos = QLabel('Remote pos:')
        self.label_remote_pos_val = QLabel(str(self.remotePos))
        self.rightLayout.addWidget(self.label_w, 0, 0)
        self.rightLayout.addWidget(self.label_w_val, 0, 1)
        self.rightLayout.addWidget(self.label_h, 1, 0)
        self.rightLayout.addWidget(self.label_h_val, 1, 1)
        self.rightLayout.addWidget(self.label_z, 2, 0)
        self.rightLayout.addWidget(self.label_z_val, 2, 1)
        self.rightLayout.addWidget(self.label_remote_pos, 3, 0)
        self.rightLayout.addWidget(self.label_remote_pos_val, 3, 1)

        #self.window_settings = WindowDraw(self)

        self.mainLayout.addLayout(self.leftLayout,0,0,1,1)
        self.mainLayout.addLayout(self.rightLayout,0,1,1,1)
        self.setLayout(self.mainLayout)
        self.show()
    
    def changeColor(self, btn): 
        if btn.isChecked(): 
            btn.setStyleSheet("background-color : lightblue") 
        else: 
            btn.setStyleSheet("background-color : lightgrey")
    
    def on_click_free(self):
        self.changeColor(self.btn_freeMode)
        if self.freeModeOn:
            self.myRobot.robot.end_freedrive_mode()
            self.freeModeOn = False
        else:
            self.myRobot.robot.freedrive_mode()
            self.freeModeOn = True


    def on_click_reset_error(self):
        self.changeColor(self.btn_freeMode)
        self.myRobot.robot.reset_error()
        self.myRobot.robot.init_realtime_control()

    def on_click_canvas_size(self):
        i , ok = QInputDialog().getInt(self, "Set Width",
                                 "Width:")
        if ok:
            self.label_w_val.setText("{}".format(i))
            self.canvasW = i
            self.settings.setValue("width", i)

        i , ok = QInputDialog().getInt(self, "Set Height",
                                 "Height:")
        if ok:
            self.label_h_val.setText("{}".format(i))
            self.canvasH = i
            self.settings.setValue("height", i)

    def on_click_z_offset(self):
        d , ok = QInputDialog().getDouble(self, "Set Z Offset",
                                 "Z:", decimals=4)
        if ok:
            self.label_z_val.setText("{}".format(d))
            self.zOffset = d
            self.settings.setValue("zOffset", d)

    def on_click_draw(self, checked):
        if self.window_draw.isVisible():
            self.window_draw.hide()
        else:
            self.window_draw.show()

    @pyqtSlot(int)
    def on_stateChanged(self, state):
        if state == MqttClient.Connected:
            print(state)
            self.client.subscribe("heart/test")

    @pyqtSlot(str)
    def on_messageSignal(self, msg):
        try:
            if self.activated:
                val = msg.split(',')
                x = int(val[0])
                y = int(val[1])
                self.label_remote_pos_val.setText(f"X: {x} | Y: {y}")
                coord = self.myRobot.PixelTranslation(x, y, self.canvasH, self.canvasW)
                z = -coord[2] + self.zOffset
                self.myRobot.robot.set_realtime_pose([coord[0], coord[1], z, 0,3.14,0])
            else:
                print("not activated")
        except ValueError:
            print("error: Parsing Error")

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
        self.myRobot.Calibrate(3, [self.canvasH, self.canvasW])
    
    @pyqtSlot()
    def on_click_activate(self):
        self.changeColor(self.btn_activate)
        self.activated = not self.activated
        if(self.activated):
            self.myRobot.constructDrawingCanvas()
            self.myRobot.calculateCroppedSizing(self.canvasH, self.canvasW)
        
    
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))

    # def closeEvent(self):
    #     self.settings.setValue("key")
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())