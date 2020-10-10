import sys, traceback
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
from Worker import Worker, WorkerSignals
from TabletWindow import WindowDraw
from Utils import figureOrientation

class App(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'RoboUI'
        self.wWidth = 600
        self.wHeight = 400

        self.settings = QSettings("RoboApp", "App")
        self._animations = {}
        with open('animations.json') as json_file:
            anims = json.load(json_file)
            self._animations = anims
            #print(anims)

        # Canvas size
        self.canvasW = self.settings.value("width") #2560
        self.canvasH = self.settings.value("height") #1440
        self.zOffset = float(self.settings.value("zOffset")) or 0 #0.04
        self.remotePos = "X: not received | Y: not received"
        self.tabletPos = "X: not received | Y: not received"

        self.initUI()
        #self.myRobot = MyRobot(host = '169.254.178.76')
        self.myRobot = MyRobot(host = '172.24.210.100')
        #self.myRobot = False
        self.activated = False
        self.freeModeOn = False
        self.selectedAnimIndex = 0
        self.isRecording = False
        self.isRecordingTablet = False
        self.isAnimationPlaying = False

        self.client = MqttClient(self)
        self.client.stateChanged.connect(self.on_stateChanged)
        self.client.messageSignal.connect(self.on_messageSignal)
        self.client.hostname = "localhost" #"172.24.210.63"
        self.client.connectToHost()

        self.threadpool = QThreadPool()

        self.window_draw = WindowDraw(self,app)

    
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
        self.btn_calib.setStyleSheet("background-color : lightgrey")

        self.btn_activate = QPushButton('Activate', self)
        self.btn_activate.setGeometry(QRect(10, 10, 200, 30))
        self.btn_activate.setCheckable(True)
        self.btn_activate.setStyleSheet("background-color : lightgrey")

        self.btn_canvas = QPushButton('Set Canvas Size', self)
        self.btn_canvas.setGeometry(QRect(10, 10, 200, 30))
        self.btn_canvas.setStyleSheet("background-color : lightgrey")

        self.btn_zOffset = QPushButton('Set Z offset', self)
        self.btn_zOffset.setGeometry(QRect(10, 10, 200, 30))
        self.btn_zOffset.setStyleSheet("background-color : lightgrey")
        
        self.btn_freeMode = QPushButton('Free mode', self)
        self.btn_freeMode.setGeometry(QRect(10, 10, 200, 30))
        self.btn_freeMode.setCheckable(True) 
        self.btn_freeMode.setStyleSheet("background-color : lightgrey")

        self.btn_resetErr = QPushButton('Reset error', self)
        self.btn_resetErr.setGeometry(QRect(10, 10, 200, 30))
        self.btn_resetErr.setStyleSheet("background-color : lightgrey")

        self.btn_draw = QPushButton('Draw', self)
        self.btn_draw.setGeometry(QRect(10, 10, 200, 30))
        self.btn_draw.setStyleSheet("background-color : lightgrey")

        self.btn_record = QPushButton('Record', self)
        self.btn_record.setGeometry(QRect(10, 10, 200, 30))
        self.btn_record.setStyleSheet("background-color : lightgrey")

        self.btn_recordTablet = QPushButton('Record Tablet', self)
        self.btn_recordTablet.setGeometry(QRect(10, 10, 200, 30))
        self.btn_recordTablet.setStyleSheet("background-color : lightgrey")

        self.btn_play = QPushButton('Play Animation', self)
        self.btn_play.setGeometry(QRect(10, 10, 200, 30))
        self.btn_play.setStyleSheet("background-color : lightgrey")
        
        self.btn_delete_row = QPushButton('Delete Selected', self)
        self.btn_delete_row.setGeometry(QRect(10, 10, 200, 30))
        self.btn_delete_row.setStyleSheet("background-color : lightgrey")

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
        self.btn_record.clicked.connect(self.on_click_record)
        self.btn_recordTablet.clicked.connect(self.on_click_record_tablet)

        self.btn_play.clicked.connect(self.on_click_play)
        self.btn_delete_row.clicked.connect(self.on_click_delete_row)

        self.entry = QStandardItemModel()
        self.animationList = QListView()
        self.animationList.setModel(self.entry)
        
        for key in self._animations.keys():
            it = QStandardItem(key)
            self.entry.appendRow(it)

        self.animationList.clicked[QModelIndex].connect(self.on_anim_listview_clicked)

        #Display text
        self.label_w = QLabel("Width:")
        self.label_w_val = QLabel(str(self.canvasW))
        self.label_h = QLabel('Height:')
        self.label_h_val = QLabel(str(self.canvasH))
        self.label_z = QLabel('Z Offset:')
        self.label_z_val = QLabel(str(self.zOffset))
        self.label_remote_pos = QLabel('Remote pos:')
        self.label_remote_pos_val = QLabel(str(self.remotePos))
        self.rightLayout.addWidget(self.label_w, 2, 0)
        self.rightLayout.addWidget(self.label_w_val, 2, 1)
        self.rightLayout.addWidget(self.label_h, 3, 0)
        self.rightLayout.addWidget(self.label_h_val, 3, 1)
        self.rightLayout.addWidget(self.label_z, 4, 0)
        self.rightLayout.addWidget(self.label_z_val, 4, 1)
        self.rightLayout.addWidget(self.label_remote_pos, 0, 0)
        self.rightLayout.addWidget(self.label_remote_pos_val, 0, 1)
        self.rightLayout.addWidget(self.animationList, 5,5)
        self.rightLayout.addWidget(self.btn_delete_row, 6,5)
        self.rightLayout.addWidget(self.btn_record,6,4)
        self.rightLayout.addWidget(self.btn_play, 6,3)
        self.rightLayout.addWidget(self.btn_recordTablet, 7,1)

        #self.window_settings = WindowDraw(self)

        self.mainLayout.addLayout(self.leftLayout,0,0,1,1)
        self.mainLayout.addLayout(self.rightLayout,0,1,1,1)
        self.setLayout(self.mainLayout)
        self.show()

    def changeColor(self, btn): 
        if btn.isChecked(): 
            btn.setStyleSheet("background-color : lightblue")
            return True
        else: 
            btn.setStyleSheet("background-color : lightgrey")
            return False
    
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

    def play(self, progress_callback):
        self.myRobot.robot.end_freedrive_mode()
        self.freeModeOn = False
        self.myRobot.robot.init_realtime_control()
        tabletData = False
        print(len(self._animations[self.selectedAnimText][0]))
        if(len(self._animations[self.selectedAnimText][0]) == 3):
            tabletData = True
        
        for pose in self._animations[self.selectedAnimText]:
            time.sleep(0.1)
            if(self.isAnimationPlaying == False):
                return "Interrupted"
            if(tabletData):
                penPressure = pose[2]
                coord = self.myRobot.PixelTranslation(pose[0], pose[1], self.canvasH, self.canvasW)
                z = -coord[2] + self.zOffset
                if penPressure < 15:
                    z = -coord[2] + 0.04
                self.myRobot.robot.set_realtime_pose([coord[0], coord[1], z, 0,3.14,0])
            else:
                self.myRobot.robot.set_realtime_pose(pose)
        return "Animation Done."

    def on_click_play(self):
        if self.isAnimationPlaying:
            self.btn_play.setStyleSheet("background-color : lightgrey")
            self.isAnimationPlaying = False
        else:
            self.isAnimationPlaying = True
            self.btn_play.setStyleSheet("background-color : lightblue")
            worker = Worker(self.play) # Any other args, kwargs are passed to the run function
            worker.signals.result.connect(self.print_play_output)
            #worker.signals.finished.connect(self.thread_complete)
            worker.signals.progress.connect(self.progress_fn)
            
            # Execute
            self.threadpool.start(worker) 
    
    def record(self, progress_callback):
        #i = 0
        #self.myRobot.robot.freedrive_mode()
        #self.freeModeOn = True
        array = []
        while self.isRecording:
            time.sleep(0.08)
            pose = self.myRobot.robot.get_actual_tcp_pose()
            array.append(pose.tolist())
            #print(i)
            #i += 1
        return array

    def on_click_record(self):
        self.btn_record.setStyleSheet("background-color : lightblue")
        if(self.isRecording):
            self.isRecording = False
            self.btn_record.setStyleSheet("background-color : lightgrey")
        else:
            self.isRecording = True
            worker = Worker(self.record) # Any other args, kwargs are passed to the run function
            worker.signals.result.connect(self.print_record_output)
            worker.signals.finished.connect(self.thread_complete)
            worker.signals.progress.connect(self.progress_fn)
            # Execute
            self.threadpool.start(worker) 

    def recordTablet(self, progress_callback):
        #i = 0
        #self.myRobot.robot.freedrive_mode()
        #self.freeModeOn = True
        array = []
        while self.isRecording:
            time.sleep(0.08)
            pose = [self.window_draw.pen_x, self.window_draw.pen_y, self.window_draw.pen_pressure]
            array.append(pose)
        return array
    
    def on_click_record_tablet(self):
        self.btn_recordTablet.setStyleSheet("background-color : lightblue")
        if(self.isRecording):
            self.isRecording = False
            self.btn_recordTablet.setStyleSheet("background-color : lightgrey")
        else:
            self.isRecording = True
            worker = Worker(self.recordTablet) # Any other args, kwargs are passed to the run function
            worker.signals.result.connect(self.print_record_output)
            worker.signals.finished.connect(self.thread_complete)
            worker.signals.progress.connect(self.progress_fn)
            # Execute
            self.threadpool.start(worker) 
        
    def on_anim_listview_clicked(self, index):
        item = self.entry.itemFromIndex(index)
        print(item.index().row(), item.text())
        self.selectedAnimIndex = item.index().row()
        self.selectedAnimText = item.text()

        #item = self.animationList.currentItem()
        #print(str(item.text()), str(self.entry.rowCount()))
    
    def on_click_delete_row(self):
        self.entry.removeRow(self.selectedAnimIndex)
        del self._animations[self.selectedAnimText]

    def print_play_output(self, s):
        self.btn_play.setStyleSheet("background-color : lightgrey")
        self.isAnimationPlaying = False
        self.myRobot.robot.init_realtime_control()
        #print(s)
    
    def print_record_output(self, data):
        print(data)
        # Prompt to save here
        s , ok = QInputDialog().getText(self, "Animation Name",
                                 "Name:")
        if ok:
            self._animations[s] = data 
            it = QStandardItem(s)
            self.entry.appendRow(it)
            with open('animations.json', 'w') as outfile:
                json.dump(self._animations, outfile)
        print(s)
        
    def thread_complete(self):
        print("THREAD COMPLETE!")

    def progress_fn(self, pose):
        print(pose)

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
                # Portrait format
                # x = int(val[1]) * (self.canvasW/self.canvasH)
                # y =  -int(val[0]) * (self.canvasH/self.canvasW) + self.canvasH
                # x = int(x)
                # y = int(y)

                #y = self.canvasH - y

                newPoint = figureOrientation([x,y],self.canvasW, self.canvasH, 0, mirrorW=True, mirrorH=True)
                print(newPoint)
                self.label_remote_pos_val.setText(f"X: {newPoint[0]} | Y: {newPoint[1]}")
                coord = self.myRobot.PixelTranslation(newPoint[0], newPoint[1], self.canvasH, self.canvasW)
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
        self.myRobot.robot.init_realtime_control()
    
    @pyqtSlot()
    def on_click_activate(self):
        self.changeColor(self.btn_activate)
        self.activated = not self.activated
        if(self.activated):
            self.myRobot.constructDrawingCanvas()
            self.myRobot.calculateCroppedSizing(self.canvasH, self.canvasW)
        
    
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))

    def on_message(self, client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))

    def closeEvent(self, event):
        #print(self._animations)
        with open('animations.json', 'w') as outfile:
            json.dump(self._animations, outfile)
            #print("JSON Saved: ", json.dumps(self._animations))
    
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()
    sys.exit(app.exec_())