import sys, traceback
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import json
import time
import scipy.interpolate
import math
import operator
import cv2
import os

# import URBasic
from MqttClient import MqttClient
from Robot import MyRobot
from Worker import Worker, WorkerSignals
from TabletWindow import WindowDraw
from Utils import figureOrientation

class App(QWidget):
	def __init__(self):
		super().__init__()
		self.title = 'RoboUI'
		self.wWidth = 800
		self.wHeight = 600

		self.settings = QSettings("RoboApp", "App")
		self._animations = {}
		with open('animations.json') as json_file:
			anims = json.load(json_file)
			self._animations = anims
			#print(anims)

		# Canvas size
		self.canvasW = self.settings.value("width") or 1920 #2560
		self.canvasH = self.settings.value("height") or 1080 #1440
		self.remotePos = "X: not received | Y: not received"
		self.tabletPos = "X: not received | Y: not received"

		#self.myRobot = MyRobot(host = '172.16.22.2')
		self.myRobot = MyRobot(host = '169.254.178.76')
		self.myRobot.SetZvals(float(self.settings.value("z_offset") or 0)) #0.04)
		self.initUI()

		#self.myRobot = False
		self.activated = False
		self.freeModeOn = False
		self.selectedAnimIndex = 0
		self.isRecording = False
		self.isRecordingTablet = False
		self.isAnimationPlaying = False
		self.isHovering = False

		# Initialize MQTT
		# self.client = MqttClient(self)
		# self.client.stateChanged.connect(self.on_stateChanged)
		# self.client.messageSignal.connect(self.on_messageSignal)
		# self.client.hostname = "localhost" #"172.24.210.63"
		# self.client.connectToHost()

		self.threadpool = QThreadPool()

		self.window_draw = WindowDraw(self,app)


	def initUI(self):
		self.setWindowTitle(self.title)
		self.mainLayout = QGridLayout()
		self.setFixedSize(self.wWidth, self.wHeight)
		self.leftLayout = QVBoxLayout()
		self.rightLayout = QGridLayout()

		# Buttons
		leftLayoutButtons = ["calibrate", "activate", "canvas_size", "z_offset", "free_mode", "draw",  "reset_error", "draw_test", "toggle_hover"]

		self.buttons = {}
		for btn in leftLayoutButtons:
			text = btn.replace("_", " ").title()
			button = QPushButton(text, self)
			button.setGeometry(QRect(10, 10, 200, 30))
			button.setCheckable(True)

			button.setStyleSheet("background-color : lightgrey")
			self.leftLayout.addWidget(button)
			button.clicked.connect(getattr(self, "on_click_" + btn))
			self.buttons[btn] = button


		rightLayoutButtons = ["record_animation", "record_tablet", "play_animation", "delete_row"]
		for i, btn in enumerate(rightLayoutButtons):
			text = btn.replace("_", " ").title()
			button = QPushButton(text, self)
			button.setGeometry(QRect(10, 10, 200, 30))
			button.setCheckable(True)
			button.setStyleSheet("background-color : lightgrey")
			button.clicked.connect(getattr(self, "on_click_" + btn))
			self.buttons[btn] = button

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
		self.label_z = QLabel('Z-Offset (cm):')
		self.label_z_val = QLabel(str(self.myRobot.zOffset))
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
		self.rightLayout.addWidget(self.animationList, 5,3,1,2)
		self.rightLayout.addWidget(self.buttons["delete_row"], 6,5)
		self.rightLayout.addWidget(self.buttons["record_animation"],6,4)
		self.rightLayout.addWidget(self.buttons["play_animation"], 6,3)
		self.rightLayout.addWidget(self.buttons["record_tablet"], 6,2)

		self.buttons["draw"].setCheckable(False)
		self.buttons["delete_row"].setCheckable(False)
		self.buttons["z_offset"].setCheckable(False)
		self.buttons["reset_error"].setCheckable(False)
		self.buttons["canvas_size"].setCheckable(False)


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

	def on_click_draw_test(self):
		dirname = os.path.dirname(__file__)
		filename = os.path.join(dirname, 'drawings/robosign.png')

		self.myRobot.RunDrawingWp(cv2.imread(filename))


	def on_click_free_mode(self):
		self.changeColor(self.buttons["free_mode"])
		if self.freeModeOn:
			self.myRobot.robot.end_freedrive_mode()
			self.freeModeOn = False
		else:
			self.myRobot.robot.freedrive_mode()
			self.freeModeOn = True

	def on_click_reset_error(self):
		self.changeColor(self.buttons["free_mode"])
		self.myRobot.robot.reset_error()
		self.myRobot.robot.init_realtime_control()

	def on_click_toggle_hover(self):
		currentPose = self.myRobot.robot.get_actual_tcp_pose()
		zVal = self.myRobot.zHover
		if self.isHovering:
			zVal = self.myRobot.zOffset
		self.isHovering = not self.isHovering
		nextPose = [currentPose[0], currentPose[1], self.myRobot.initHoverPos[2] + zVal, self.myRobot.endPntPose[3], self.myRobot.endPntPose[4], self.myRobot.endPntPose[5]]
		self.myRobot.ExecuteSinglePath(nextPose)

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
								 "Z:", decimals=2)
		if ok:
			self.label_z_val.setText("{}".format(d))
			self.myRobot.SetZvals(d, division=100)
			#pose = self.myRobot.robot.get_actual_tcp_pose()
			#adjustedPose = [pose[0],pose[1],pose[2] + d, pose[3], pose[4], pose[5]]
			#self.myRobot.robot.set_realtime_pose(adjustedPose)
			self.settings.setValue("z_offset", d)

	def on_click_draw(self, checked):
		if self.window_draw.isVisible():
			self.window_draw.hide()
		else:
			self.window_draw.show()

	def play(self, progress_callback):
		self.myRobot.robot.end_freedrive_mode()
		self.freeModeOn = False

		# Move to middle before starting
		#middle = [0.3,0.3,0.3, 0,3.14,0]
		#self.myRobot.robot.movej(pose=middle, a=1.2, v=0.9)
		#if(self.myRobot.robot.get_actual_tcp_pose() == middle):

		self.myRobot.robot.init_realtime_control()
		tabletData = False
		if(len(self._animations[self.selectedAnimText][0]) == 3):
			tabletData = True
		for pose in self._animations[self.selectedAnimText]:
			time.sleep(0.115)
			if(self.isAnimationPlaying == False):
				return "Interrupted"
			if(tabletData):
				penPressure = pose[2]
				coord = self.myRobot.PixelTranslation(pose[0], pose[1], self.canvasH, self.canvasW)
				z = -coord[2] + self.myRobot.zOffset
				if penPressure < 15:
					z = -coord[2] + 0.04
				self.myRobot.robot.set_realtime_pose([coord[0], coord[1], z, 0,3.14,0])
			else:
				self.myRobot.robot.set_realtime_pose(pose)
		return "Animation Done."

	def on_click_play_animation(self):
		if self.isAnimationPlaying:
			self.buttons["play_animation"].setStyleSheet("background-color : lightgrey")
			self.isAnimationPlaying = False
		else:
			self.isAnimationPlaying = True
			self.buttons["play_animation"].setStyleSheet("background-color : lightblue")
			worker = Worker(self.play) # Any other args, kwargs are passed to the run function
			worker.signals.result.connect(self.print_play_output)
			#worker.signals.finished.connect(self.thread_complete)
			worker.signals.progress.connect(self.progress_fn)

			# Execute
			self.threadpool.start(worker)

	def record(self, progress_callback):
		array = []
		while self.isRecording:
			time.sleep(0.115)
			pose = self.myRobot.robot.get_actual_tcp_pose()
			array.append(pose.tolist())
		return array

	def on_click_record_animation(self):
		self.buttons["record_animation"].setStyleSheet("background-color : lightblue")
		if(self.isRecording):
			self.isRecording = False
			self.buttons["record_animation"].setStyleSheet("background-color : lightgrey")
		else:
			self.isRecording = True
			worker = Worker(self.record) # Any other args, kwargs are passed to the run function
			worker.signals.result.connect(self.print_record_output)
			worker.signals.finished.connect(self.thread_complete)
			worker.signals.progress.connect(self.progress_fn)
			# Execute
			self.threadpool.start(worker)

	def recordTablet(self):
		array = []
		while self.isRecording:
			time.sleep(0.1)
			pose = [self.window_draw.pen_x, self.window_draw.pen_y, self.window_draw.pen_pressure]
			array.append(pose)
		return array

	def on_click_record_tablet(self):
		self.buttons["record_tablet"].setStyleSheet("background-color : lightblue")
		if(self.isRecording):
			self.isRecording = False
			self.buttons["record_tablet"].setStyleSheet("background-color : lightgrey")
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

	def on_click_delete_row(self):
		self.entry.removeRow(self.selectedAnimIndex)
		del self._animations[self.selectedAnimText]

	def print_play_output(self, s):
		self.buttons["play_animation"].setStyleSheet("background-color : lightgrey")
		self.isAnimationPlaying = False
		self.myRobot.robot.init_realtime_control()

	def print_record_output(self, data):
		s , ok = QInputDialog().getText(self, "Animation Name",
								 "Name:")
		if ok:
			self._animations[s] = data
			it = QStandardItem(s)
			self.entry.appendRow(it)
			with open('animations.json', 'w') as outfile:
				json.dump(self._animations, outfile)

	def thread_complete(self):
		print("THREAD COMPLETE!")

	def progress_fn(self, pose):
		print(pose)

	# Subrscibe to MQTT messages
	# @pyqtSlot(int)
	# def on_stateChanged(self, state):
	# 	if state == MqttClient.Connected:
	# 		print(state)
	# 		self.client.subscribe("heart/test")

	@pyqtSlot(str)
	def on_messageSignal(self, msg):
		try:
			if self.activated:
				val = msg.split(',')
				x = int(val[0])
				y = int(val[1])
				newPoint = figureOrientation([x,y],self.canvasW, self.canvasH, rotation=1, mirrorW=True, mirrorH=True)
				#print(x,y, newPoint)
				self.label_remote_pos_val.setText(f"X: {newPoint[0]} | Y: {newPoint[1]}")
				coord = self.myRobot.PixelTranslation(newPoint[0], newPoint[1], self.canvasH, self.canvasW)
				z = -coord[2] + self.myRobot.zOffset
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
		self.changeColor(self.buttons["activate"])
		self.activated = not self.activated
		if(self.activated):
			self.myRobot.robot.init_realtime_control()
			self.myRobot.constructDrawingCanvas()
			self.myRobot.calculateCroppedSizing(self.canvasH, self.canvasW)


	def on_connect(self, client, userdata, flags, rc):
		print("Connected with result code "+str(rc))

	#def on_message(self, client, userdata, msg):
		#print(msg.topic+" "+str(msg.payload))

	def closeEvent(self, event):
		with open('animations.json', 'w') as outfile:
			json.dump(self._animations, outfile)
			#print("JSON Saved: ", json.dumps(self._animations))

if __name__ == '__main__':
	app = QApplication(sys.argv)
	App()
	sys.exit(app.exec_())
