import sys, traceback
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import json
import time
import scipy.interpolate
import math
import operator
import os
import random 

# import URBasic
# from MqttClient import MqttClient
from Robot import MyRobot
from Worker import Worker, WorkerSignals
from TabletWindow import WindowDraw
from Utils import figureOrientation

class App(QWidget):
	def __init__(self):
		super().__init__()
		self.title = 'RoboUI'
		self.wWidth = 1200
		self.wHeight = 860

		self.settings = QSettings("RoboApp", "App")
		self._images = {}

		for file in os.listdir("drawings"):
			if file.endswith(".jpg") or file.endswith(".png"):
				self._images.update({file.split(".")[0]: os.path.join("drawings", file)})

		with open('./data/animations.json') as json_file:
			anims = json.load(json_file)
			self._animations = anims

		with open('./data/drawings.json') as json_file:
			f = json.load(json_file)
			self._drawings = f

		# Canvas size
		self.canvasW = self.settings.value("width") or 1920 #2560
		self.canvasH = self.settings.value("height") or 1080 #1440
		self.remotePos = "X: not received | Y: not received"
		self.tabletPos = "X: not received | Y: not received"

		self.myRobot = MyRobot(app=self, host = '192.168.1.100')
		# self.myRobot = MyRobot(host = '192.168.1.100')
		self.myRobot.SetZvals(float(self.settings.value("z_offset") or 0), division=100) #0.04)
		self.initUI()

		#self.myRobot = False
		self.activated = False
		self.freeModeOn = False

		self.selectedAnimIndex = 0
		self.selectedFileIndex = 0
		self.selectedDrawIndex = 0

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
		self.leftLayout = QGridLayout()
		self.rightLayout = QGridLayout()
		self.midLayout = QGridLayout()


		# Buttons
		self.disabledButtons = ["play_animation", "play_drawing", "sit", "greet", "draw_random", "contemplate", "pen", "yes", "no"]
		leftLayoutButtons = ["calibrate", "activate", "canvas_size", "z_offset", "free_mode", "draw",  "reset_error", "toggle_hover", "stop_robot",  "sit", "greet", "draw_random", "contemplate", "pen", "yes", "no"]

		self.buttons = {}
		for btn in leftLayoutButtons:
			text = btn.replace("_", " ").title()
			button = QPushButton(text, self)
			button.setGeometry(QRect(10, 10, 200, 30))
			button.setCheckable(True)


			if btn == "sit":
				button.setContentsMargins(0,50,0,0)

			button.setStyleSheet("background-color : lightgrey")
			self.leftLayout.addWidget(button)
			button.clicked.connect(getattr(self, "on_click_" + btn))
			self.buttons[btn] = button


		rightLayoutButtons = ["play_drawing", "record_animation", "record_tablet", "play_animation", "delete_row", "delete_row_draw"]
		for i, btn in enumerate(rightLayoutButtons):
			text = btn.replace("_", " ").title()
			button = QPushButton(text, self)
			button.setGeometry(QRect(10, 10, 200, 30))
			button.setCheckable(True)
			button.setStyleSheet("background-color : lightgrey")
			button.clicked.connect(getattr(self, "on_click_" + btn))
			self.buttons[btn] = button

		self.image_frame = QLabel()

		self.animEntry = QStandardItemModel()
		self.animationList = QListView()
		self.animationList.setModel(self.animEntry)

		self.drawEntry = QStandardItemModel()
		self.drawList = QListView()
		self.drawList.setModel(self.drawEntry)

		self.fileEntry = QStandardItemModel()
		self.fileList = QListView()
		self.fileList.setModel(self.fileEntry)

		for key in self._animations.keys():
			it = QStandardItem(key)
			self.animEntry.appendRow(it)

		# iterate through files in folder
		# for key in self._images.keys():
		# 	it = QStandardItem(key)
		# 	self.fileEntry.appendRow(it)

		for key in self._drawings.keys():
			it = QStandardItem(key)
			self.drawEntry.appendRow(it)

		self.animationList.clicked[QModelIndex].connect(self.on_anim_listview_clicked)
		self.drawList.clicked[QModelIndex].connect(self.on_draw_listview_clicked)
		# self.fileList.clicked[QModelIndex].connect(self.on_file_listview_clicked)
		# self.fileList.setCurrentIndex(self.fileEntry.index(0, 0))
		# self.on_file_listview_clicked(self.fileEntry.index(0, 0))

		self.image_frame.setContentsMargins(0,20,0,0)


		self.label_w = QLabel("Width:")
		self.label_w_val = QLabel(str(self.canvasW))
		self.label_h = QLabel('Height:')
		self.label_h_val = QLabel(str(self.canvasH))
		self.label_z = QLabel('Z-Offset (cm):')
		self.label_z_val = QLabel(str(self.myRobot.zOffset))
		self.label_remote_pos = QLabel('Remote pos:')
		self.label_remote_pos_val = QLabel(str(self.remotePos))
		self.label_anim = QLabel("Animations:")
		self.label_drawings = QLabel("Drawings:")
		self.midLayout.addWidget(self.label_w, 2, 0)
		self.midLayout.addWidget(self.label_w_val, 2, 1)
		self.midLayout.addWidget(self.label_h, 3, 0)
		self.midLayout.addWidget(self.label_h_val, 3, 1)
		self.midLayout.addWidget(self.label_z, 4, 0)
		self.midLayout.addWidget(self.label_z_val, 4, 1)
		self.midLayout.addWidget(self.label_remote_pos, 0, 0)
		self.midLayout.addWidget(self.label_remote_pos_val, 0, 1)
		self.rightLayout.addWidget(self.label_anim, 4,4)
		self.rightLayout.addWidget(self.animationList, 5,4,1,2)
		self.rightLayout.addWidget(self.label_drawings, 4,2)
		self.rightLayout.addWidget(self.drawList, 5,2,1,2)
		# self.rightLayout.addWidget(self.fileList, 5,2,1,2)
		self.midLayout.addWidget(self.image_frame, 11,0,1,2)
		self.rightLayout.addWidget(self.buttons["play_drawing"], 3,2)
		self.rightLayout.addWidget(self.buttons["play_animation"], 3,4)
		self.rightLayout.addWidget(self.buttons["record_animation"],8,5)
		self.rightLayout.addWidget(self.buttons["record_tablet"], 9,5)
		self.rightLayout.addWidget(self.buttons["delete_row"], 10,5)
		self.rightLayout.addWidget(self.buttons["delete_row_draw"], 10,3)

		self.buttons["draw"].setCheckable(False)
		self.buttons["delete_row"].setCheckable(False)
		self.buttons["z_offset"].setCheckable(False)
		self.buttons["reset_error"].setCheckable(False)
		self.buttons["canvas_size"].setCheckable(False)
		self.buttons["stop_robot"].setCheckable(False)
		self.buttons["play_animation"].setCheckable(False)
		self.buttons["play_drawing"].setCheckable(False)

		for btn in self.disabledButtons:
			self.buttons[btn].setCheckable(False)

		self.midLayout.setContentsMargins(0,0,75,0)

		self.mainLayout.addLayout(self.leftLayout,0,3,1,1, Qt.AlignTop)
		self.mainLayout.addLayout(self.rightLayout,0,2,1,1)
		self.mainLayout.addLayout(self.midLayout,0,1,1,1, Qt.AlignTop)

		self.setLayout(self.mainLayout)
		self.show()

	def changeColor(self, btn):
		if btn.isChecked():
			btn.setStyleSheet("background-color : lightblue")
			return True
		else:
			btn.setStyleSheet("background-color : lightgrey")
			return False

	# def on_click_play_drawing(self):
	# 	path = "/" + self._drawings[self.fileList.currentIndex().data()]
	# 	self.myRobot.RunDrawingWpt(path)

	def on_click_stop_robot(self):
		self.myRobot.robot.stopl()

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

	def on_click_toggle_hover(self):
		currentPose = self.myRobot.robot.get_actual_tcp_pose()
		zVal = self.myRobot.zHover
		if self.isHovering:
			zVal = self.myRobot.zOffset
		self.isHovering = not self.isHovering
		nextPose = [currentPose[0], currentPose[1], -self.myRobot.initHoverPos[2] + zVal, self.myRobot.toolRotation[0], self.myRobot.toolRotation[1], self.myRobot.toolRotation[2]]
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
			self.settings.setValue("z_offset", d)

	def on_click_draw(self, checked):
		if self.window_draw.isVisible():
			self.window_draw.hide()
		else:
			self.myRobot.robot.init_realtime_control_pose()
			self.window_draw.show()

	def end_freedrive(self):
		self.myRobot.robot.end_freedrive_mode()
		self.buttons["free_mode"].setStyleSheet("background-color : lightgrey")
		self.freeModeOn = False

	def playAnim(self, progress_callback):
		self.end_freedrive()
		animation = self._animations[self.selectedAnimText]
		result = self.myRobot.playAnimation(animation)
		print(result)

	def playDrawing(self, progress_callback):
		self.end_freedrive()
		drawing = self._drawings[self.selectedDrawText]
		result = self.myRobot.playAnimation(drawing)
		print(result)

	def on_click_play_animation(self):
		self.isAnimationPlaying = True
		for btn in self.disabledButtons:
			self.buttons[btn].setEnabled(False)
			self.buttons[btn].setStyleSheet("background-color : lightblue")
		worker = Worker(self.playAnim) # Any other args, kwargs are passed to the run function
		worker.signals.result.connect(self.print_play_output)
		worker.signals.progress.connect(self.progress_fn)

		# Execute
		self.threadpool.start(worker)

	def on_click_play_drawing(self):
		self.isAnimationPlaying = True
		for btn in self.disabledButtons:
			self.buttons[btn].setEnabled(False)
			self.buttons[btn].setStyleSheet("background-color : lightblue")
		worker = Worker(self.playDrawing) # Any other args, kwargs are passed to the run function
		worker.signals.result.connect(self.print_play_output)
		worker.signals.progress.connect(self.progress_fn)

		# Execute
		self.threadpool.start(worker)

	def record(self, progress_callback):
		array = []
		while self.isRecording:
			time.sleep(0.115)
			pose = self.myRobot.robot.get_actual_joint_positions()
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

	def recordTablet(self, progress_callback):
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
			worker.signals.result.connect(self.print_record_output_tablet)
			worker.signals.finished.connect(self.thread_complete)
			worker.signals.progress.connect(self.progress_fn)
			# Execute
			self.threadpool.start(worker)

	def on_anim_listview_clicked(self, index):
		item = self.animEntry.itemFromIndex(index)
		self.selectedAnimIndex = item.index().row()
		self.selectedAnimText = item.text()

	def on_draw_listview_clicked(self, index):
		item = self.drawEntry.itemFromIndex(index)
		self.selectedDrawIndex = item.index().row()
		self.selectedDrawText = item.text()

	# def on_file_listview_clicked(self, index):
	# 	item = self.fileEntry.itemFromIndex(index)
	# 	self.selectedFileIndex = item.index().row()
	# 	self.selectedFileText = item.text()

	# 	imgPath = "/" + self._drawings[self.fileList.currentIndex().data()]
	# 	cvImg = self.myRobot.GetDrawingPreview(imgPath)
	# 	im = QImage(cvImg.data, cvImg.shape[1], cvImg.shape[0], cvImg.strides[0], QImage.Format_RGB888).rgbSwapped()
	# 	pix = QPixmap.fromImage(im)
	# 	pix = pix.scaled(600, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
	# 	self.image_frame.setPixmap(pix)


	def on_click_delete_row(self):
		self.animEntry.removeRow(self.selectedAnimIndex)
		del self._animations[self.selectedAnimText]
		if(self.selectedAnimIndex != 0):
			self.selectedAnimIndex -= 1
			self.selectedAnimText = self.animEntry.item(self.selectedAnimIndex).text()
		else:
			self.selectedAnimIndex = 0

	def on_click_delete_row_draw(self):
		self.drawEntry.removeRow(self.selectedDrawIndex)
		del self._drawings[self.selectedDrawText]
		if(self.selectedDrawIndex != 0):
			self.selectedDrawIndex -= 1
			self.selectedDrawText = self.drawEntry.item(self.selectedDrawIndex).text()
		else:
			self.selectedDrawIndex = 0
		

	def print_play_output(self, s):
		self.manageAnimButtons(enable=True)
		self.isAnimationPlaying = False

	def print_record_output(self, data):
		s , ok = QInputDialog().getText(self, "Animation Name",
								 "Name:")
		if ok:
			self._animations[s] = data
			it = QStandardItem(s)
			self.animEntry.appendRow(it)
			with open('./data/animations.json', 'w') as outfile:
				json.dump(self._animations, outfile)
	
	def print_record_output_tablet(self, data):
		s , ok = QInputDialog().getText(self, "Drawing Name",
								 "Name:")
		if ok:
			self._drawings[s] = data
			it = QStandardItem(s)
			self.drawEntry.appendRow(it)
			with open('./data/drawings.json', 'w') as outfile:
				json.dump(self._drawings, outfile)

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

	# @pyqtSlot(str)
	# def on_messageSignal(self, msg):
	# 	try:
	# 		if self.activated:
	# 			val = msg.split(',')
	# 			x = int(val[0])
	# 			y = int(val[1])
	# 			newPoint = figureOrientation([x,y],self.canvasW, self.canvasH, rotation=1, mirrorW=True, mirrorH=True)
	# 			#print(x,y, newPoint)
	# 			self.label_remote_pos_val.setText(f"X: {newPoint[0]} | Y: {newPoint[1]}")
	# 			coord = self.myRobot.PixelTranslation(newPoint[0], newPoint[1], self.canvasH, self.canvasW)
	# 			z = -coord[2] + self.myRobot.zOffset
	# 			self.myRobot.robot.set_realtime_pose([coord[0], coord[1], z, 0,3.14,0])
	# 		else:
	# 			print("not activated")
	# 	except ValueError:
	# 		print("error: Parsing Error")

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
		self.myRobot.Calibrate(3, size = [self.canvasH, self.canvasW])

	@pyqtSlot()
	def on_click_activate(self):
		self.changeColor(self.buttons["activate"])
		self.activated = not self.activated
		if(self.activated):
			self.myRobot.constructDrawingCanvas()
			self.myRobot.calculateCroppedSizing(self.canvasH, self.canvasW)


	# def on_connect(self, client, userdata, flags, rc):
	# 	print("Connected with result code "+str(rc))

	#def on_message(self, client, userdata, msg):
		#print(msg.topic+" "+str(msg.payload))

	def closeEvent(self, event):
		with open('./data/animations.json', 'w') as outfile:
			json.dump(self._animations, outfile)
		
		with open('./data/drawings.json', 'w') as outfile:
			json.dump(self._drawings, outfile)


	def manageAnimButtons(self, enable):
		if enable:
			for btn in self.disabledButtons:
				self.buttons[btn].setEnabled(True)
				self.buttons[btn].setStyleSheet("background-color : lightgray")
		else:
			for btn in self.disabledButtons:
				self.buttons[btn].setEnabled(False)
				self.buttons[btn].setStyleSheet("background-color : lightblue")

	def on_click_sit(self):
		self.manageAnimButtons(enable=False)
		self.selectedAnimText = "StationaryPosition"
		self.on_click_play_animation()

	def on_click_greet(self):
		self.manageAnimButtons(enable=False)
		self.selectedAnimText = "Greeting"
		self.on_click_play_animation()
	
	def on_click_draw_random(self):
		self.manageAnimButtons(enable=False)
		randomKey = list(self._drawings)[random.randint(0,len(self._drawings)-1)]
		self.selectedDrawText = randomKey
		self.on_click_play_drawing()

	def on_click_contemplate(self):
		self.manageAnimButtons(enable=False)

		self.selectedAnimText = "ContemplateLatest"
		self.on_click_play_animation()
	
	def on_click_pen(self):
		self.manageAnimButtons(enable=False)
		self.selectedAnimText = "PenPoint"
		self.on_click_play_animation()

	def on_click_yes(self):
		self.manageAnimButtons(enable=False)
		self.selectedAnimText = "yes"
		self.on_click_play_animation()
	
	def on_click_no(self):
		self.manageAnimButtons(enable=False)
		self.selectedAnimText = "no"
		self.on_click_play_animation()


if __name__ == '__main__':
	app = QApplication(sys.argv)
	App()
	sys.exit(app.exec_())
