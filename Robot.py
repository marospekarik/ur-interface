import URBasic
import numpy as np
import time
import math
import csv
import random
import json
import ContourExtraction
import cv2
import os
import matplotlib.pyplot as plt
from Worker import Worker, WorkerSignals

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

#defaultHost = '172.24.210.207'
#defaultHost = '127.0.0.1'
#defaultHost = '169.254.178.76'

#10.0.0.15
#acc = 0.9
#vel = 0.9

class MyRobot(URBasic.urScriptExt.UrScriptExt):
	def __init__(self, host, app):
		print("Robot connecting to: ", host)
		robotModle = URBasic.robotModel.RobotModel()
		self.robot = URBasic.urScriptExt.UrScriptExt(host=host,robotModel=robotModle)
		self.robot.reset_error()

		#TO DO: SLOW DOWN THIS KILLING MACHINE SOMEHOW
		#self.robot.init_force_remote()
		#self.robot.set_force_remote(limits=[0.05, 0.05, 0.05,0.05, 0.05, 0.05])

		# Speed parameters
		self.a = 0.3
		self.v = 0.3

		self.ui = app
		 # The parameters of the calibrated canvas
		self.canvasWidth = 0
		self.canvasHeight = 0
		self.canvasMidpoint = 0
		#cropped sizing
		self.canvasCroppedWidth = 0
		self.canvasCroppedHeight = 0
		self.xShift = 0
		self.zHover = 0

		# Save each recorded calibrated point into this class
		with open('./data/calibration_points.json') as json_file:
			points = json.load(json_file)
			self.bottomLeftPoint = points["bottomLeft"]
			self.topLeftPoint = points["topLeft"]
			self.topRightPoint  = points["topRight"]
			self.bottomRightPoint = points["bottomRight"]

		# These parameters represent the variables for translating the alternative values to new coordinates of drawing
		self.theta = 0
		self.Xr = 0
		self.Yr = 0

		self.heightErrorDisplacement = 0

		# The horizontal Planular Equations
		# ax + by + cz + d = 0
		self.plE1_a = 0
		self.plE1_b = 0
		self.plE1_c = 0
		self.plE1_d = 0

		self.ExtraContours = []

		self.zOffset = 0
		self.ep_valP=[0,0]
		self.dist_threshP=[0,0]
		self.toolRotation = [-3.141369099840455, -0.023765232731069934, -0.018604100882098216]
		self.initHoverPos = [0,0,0]
		self.initTargetDrawPose = [0.30981093645095825, -1.9617646376239222, -2.1000917593585413, -0.6482990423785608, -4.705995742474691, -4.402732316647665]

		self.listWpt = []

		return

	def constructDrawingCanvas(self):
		p1 = np.array(self.bottomLeftPoint)
		p2 = np.array(self.bottomRightPoint)
		p3 = np.array(self.topLeftPoint)
		# print p1,p2,p3
		v1 = p3 - p1
		v2 = p2 - p1
		cp = np.cross(v1, v2)
		a, b, c = cp
		d = np.dot(cp, p3)
		self.plE1_a = a
		self.plE1_b = b
		self.plE1_c = c
		self.plE1_d = d

		# Display the resulting error margin of the constructed canvas
		testingInputTopRight = self.projectPointToPlane(self.topRightPoint[0], self.topRightPoint[1])
		self.heightErrorDisplacement = testingInputTopRight - self.topRightPoint[2]
		print('Error of ', self.heightErrorDisplacement, ' found')

		# Estimate the canvas width
		bottomWidth = math.sqrt(pow((self.bottomRightPoint[0] - self.bottomLeftPoint[0]) , 2) + pow((self.bottomRightPoint[1] - self.bottomLeftPoint[1]), 2))
		topWidth = math.sqrt(pow((self.topRightPoint[0] - self.topLeftPoint[0]), 2) + pow((self.topRightPoint[1] - self.topLeftPoint[1]), 2))
		self.canvasWidth = (bottomWidth + topWidth) / 2

		# Estimate the canvas height
		leftHeight = math.sqrt(pow((self.topLeftPoint[0] - self.bottomLeftPoint[0]), 2) + pow((self.topLeftPoint[1] - self.bottomLeftPoint[1]), 2))
		rightHeight = math.sqrt(pow((self.topRightPoint[0] - self.bottomRightPoint[0]), 2) + pow((self.topRightPoint[1] - self.bottomRightPoint[1]), 2))
		self.canvasHeight = (leftHeight + rightHeight) / 2

		self.Xr = self.bottomLeftPoint[0]
		self.Yr = self.bottomLeftPoint[1]

		# Find Theta of the canvas
		# In this method we simply calculate the angles from the theta transform to ours
		angA = math.atan2(self.bottomRightPoint[1] - self.bottomLeftPoint[1], self.bottomRightPoint[0] - self.bottomLeftPoint[0])
		angB = math.atan2(self.topRightPoint[1] - self.topLeftPoint[1],
						  self.topRightPoint[0] - self.topLeftPoint[0])
		#angA = math.atan2(self.topLeftPoint[1] - self.bottomLeftPoint[1], self.topLeftPoint[0] - self.bottomLeftPoint[0])
		#angB = math.atan2(self.topRightPoint[1] - self.bottomRightPoint[1],self.topRightPoint[0] - self.bottomRightPoint[0])
		self.theta = (angA + angB) / 2

		# find the canvas midpoint
		# BLTR
		xM1 = (self.bottomLeftPoint[0] + self.topRightPoint[0]) / 2
		yM1 = (self.bottomLeftPoint[1] + self.topRightPoint[1]) / 2

		xM2 = (self.bottomRightPoint[0] + self.topLeftPoint[0]) / 2
		yM2 = (self.bottomRightPoint[1] + self.topLeftPoint[1]) / 2

		self.canvasMidpoint = [(xM1 + xM2) / 2, (yM1 + yM2) / 2]

		#
		Zini = self.projectPointToPlane(self.canvasMidpoint[0], self.canvasMidpoint[1])
		self.initHoverPos = [self.canvasMidpoint[0], self.canvasMidpoint[1], Zini, 2.213345336120183,-2.212550352198813, 0.01]
		return

	def calculateCroppedSizing(self,imgHeight,imgWidth):
		#ratio of height to width of image
		imgRatio = (float)(imgHeight)/imgWidth
		#canvas ratio
		canvasRatio = (float)(self.canvasHeight)/self.canvasWidth
		#when canvas ratio is less than image, we crop the width
		theta = math.atan(imgRatio)
		if canvasRatio<imgRatio:
			self.canvasCroppedHeight = self.canvasHeight
			self.canvasCroppedWidth = self.canvasHeight / math.tan(theta)
			self.xShift = (self.canvasWidth - self.canvasCroppedWidth) / 2
		elif imgRatio>canvasRatio:
			self.canvasCroppedWidth = self.canvasWidth
			self.canvasCroppedHeight = self.canvasWidth * math.tan(theta)
			self.xShift = 0
		else:
			self.canvasCroppedWidth = self.canvasWidth
			self.canvasCroppedHeight = self.canvasHeight
			self.xShift = 0


		print('DIMENSIONS FOR EVALUATION')
		print(f'imgRation: {imgRatio}')
		print(f'canvasRatio: {canvasRatio}')
		print(f'imgD: {imgWidth}, {imgHeight}')
		print(f'canvasD: {self.canvasWidth} {self.canvasHeight}')
		print(f'canvasCroppedWidth: {self.canvasCroppedWidth} canvasCroppedHeight: {self.canvasCroppedHeight}')
		return

	def projectPointToPlane(self,x, y):
		return -(self.plE1_a * x + self.plE1_b * y + self.plE1_d) / self.plE1_c

	def cropPlaneToImage(self):
		return

	def scalePixelsToWorldCoordinates(self,Xi, Yi,imageWidth,imageHeight):
		xS = Xi * (self.canvasCroppedWidth / imageWidth)
		yS = Yi * (self.canvasCroppedHeight / imageHeight)
		return np.array([xS, yS])

	def getTranslatedPositionComponents(self,x, y):
		xS = x+self.xShift
		xR = self.Xr + xS * math.cos(self.theta) - y * math.sin(self.theta)
		yR = self.Yr + y * math.cos(self.theta) + x * math.sin(self.theta)
		return np.array([xR, yR])

	# This code recieves contour points input along the waypoints and converts them to real world systems
	def PixelTranslation(self, xInput, yInput, imageH, imageW):
		'''xS = xInput * (self.canvasWidth / imageWidth)
		yS = yInput * (self.canvasHeight / imageHeight)
		xR = self.Xr + xS * math.cos(self.theta) - yS * math.sin(self.theta)
		yR = self.Yr + yS * math.cos(self.theta) + xS * math.sin(self.theta)
		zR = (-self.plE1_a * xR - self.plE1_b * yR - self.plE1_d) / self.plE1_c
		return [xR,yR,zR]
		'''


		s2 = self.scalePixelsToWorldCoordinates(Xi=xInput, Yi=yInput,imageWidth=imageW,imageHeight=imageH)
		s3 = self.getTranslatedPositionComponents(x=s2[0], y=s2[1])
		return [s3[0], s3[1], self.projectPointToPlane(x=s3[0], y=s3[1])]


	def SetZvals(self, zD, division = 1):
		self.zOffset = zD / division
		self.zHover = self.zOffset + 0.04
		return

	def findIntecepts(self, originpt, horizontalpt, verticalpt):
		# get vertical lines
		pts = [originpt,
			   [originpt[0], verticalpt[1]],
			   [horizontalpt[0], originpt[1]],
			   [horizontalpt[0], verticalpt[1]]]
		return pts

	def setMax_Min(self, btmLft, btmRht, TpLft, TpRht):
		mintercepts = self.findIntecepts([btmLft[0], btmLft[1]], [btmRht[0], btmRht[1]], [TpLft[0], TpLft[1]])
		maxtercepts = self.findIntecepts([TpRht[0], TpRht[1]], [TpLft[0], TpLft[1]], [btmRht[0], btmRht[1]])
		# find the minimum euclidean distance
		minDist = float(50)
		xZero = 0
		yZero = 0
		xMax = 0
		yMax = 0
		for Min in mintercepts:
			for Max in maxtercepts:
				if (minDist > math.sqrt((Max[0] - Min[0]) ** 2 + (Max[1] - Min[1]) ** 2)):
					xZero = Min[0]
					yZero = Min[1]
					xMax = Max[0]
					yMax = Max[1]

		self.SetZvals(float(sum([btmLft[2], btmRht[2], TpLft[2], TpRht[2]]) / 4))

		return xMax, xZero, yMax, yZero

	def midpoint(self, p1, p2):
		return [float((p1[0] + p2[0]) / 2), float((p1[1] + p2[1]) / 2)]

	def PrintAllVar(self):
		print('Bottom Left Point',self.bottomLeftPoint)
		print('Top Left Point',self.topLeftPoint)
		print('Top Right Point',self.topRightPoint)
		print('Bottom Right Point',self.bottomRightPoint)
		print('Theta',self.theta)
		print('Relative X pose',self.Xr)
		print('Relative Y pose',self.Yr)
		print('Canvas Width', self.canvasWidth)
		print('Canvas Height',self.canvasHeight)
		print('Canvas Midpoint',self.canvasMidpoint)
		return

	def getCalibPt(self):
		self.robot.end_freedrive_mode()
		calPt = self.robot.get_actual_tcp_pose()
		print(calPt[0], calPt[1], calPt[2])
		return calPt

	def Calibrate(self, corner, size = [0, 0]):
		if corner == 0:
			calPt = self.getCalibPt()
			self.bottomLeftPoint = [calPt[0], calPt[1], calPt[2], ]
			self.robot.freedrive_mode()
		if corner == 1:
			calPt = self.getCalibPt()
			self.topLeftPoint = [calPt[0], calPt[1], calPt[2], ]
			self.robot.freedrive_mode()
		if corner == 2:
			calPt = self.getCalibPt()
			self.topRightPoint = [calPt[0], calPt[1], calPt[2], ]
			self.robot.freedrive_mode()
		if corner == 3:
			calPt = self.getCalibPt()
			self.bottomRightPoint = [calPt[0], calPt[1], calPt[2], ]
			self.constructDrawingCanvas()
			self.calculateCroppedSizing(size[0], size[1])

			self.PrintAllVar()
			data = {
				"bottomLeft": self.bottomLeftPoint,
				"topLeft": self.topLeftPoint,
				"topRight": self.topRightPoint,
				"bottomRight": self.bottomRightPoint
			}
			with open('./data/calibration_points.json', 'w') as outfile:
				json.dump(data, outfile)
				print("JSON Saved: ", json.dumps(data))

		# setMax_Min(self, self.bottomLeftPoint, self.topLeftPoint, self.topRightPoint, self.bottomRightPoint)
		return

	def GetDrawingPreview(self, imgPath):
		path = os.path.dirname( __file__ ) + imgPath
		image = cv2.imread(path, 0)
		[lines, img] = ContourExtraction.JamesContourAlg(image,self.ep_valP[0],self.dist_threshP[0])
		return img

	def RunDrawingWpt(self,imgPath,inputVals=0):
		listWpt = []
		maxAcc = 0.2
		maxVel = 0.3
		initTargetPose = [0.07033279538154602, -1.5860512892352503, -1.3597491423236292, -1.7119396368609827, -4.690964881573812, -4.965108100567953]

		def addNewWpt(eachPoint, newCountour = False):
			x, y, z  = self.PixelTranslation(eachPoint[0], eachPoint[1], image.shape[0], image.shape[1])
			offset = self.zHover if newCountour else self.zOffset
			pose = [x,y,-z + offset,self.toolRotation[0],self.toolRotation[1],self.toolRotation[2]]
			robotCoordFormat = {'pose': pose, 'a':maxAcc, 'v':maxVel, 't':0, 'r':0.004}
			listWpt.append(robotCoordFormat)
			return [x,y]

		path = os.path.dirname( __file__ ) + imgPath
		image = cv2.imread(path, 0)
		[lines, img] = ContourExtraction.JamesContourAlg(image,self.ep_valP[inputVals],self.dist_threshP[inputVals])

		#Crop the image space to match the input image size
		self.calculateCroppedSizing(image.shape[0], image.shape[1])
		line_num = 0

		for q in range(0,len(lines)):
			line = lines[q]
			line_num += 1
			downsampledLine = np.array(line)[::3]
			# Jump to another line
			addNewWpt([downsampledLine[0,0], downsampledLine[0,1]], newCountour=True)
			plotData = []
			if len(downsampledLine)>0:
				for eachPoint in downsampledLine:
					[plotX, plotY] = addNewWpt(eachPoint)
					plotData.append([plotX,plotY])
			self.plotTrajectory(plotData)

		plt.show()
		self.wpts = listWpt
		# initTargetPose = listWpt[0]["pose"]
		self.ExecuteSingleLinearJoint(self.initTargetDrawPose, a=0.2, v=0.4)
		self.draw_waypoints_worker()
		return

	def plotTrajectory(self, eachPoint):
		arr = np.array(eachPoint)
		plt.plot(arr[:,1],arr[:,0])

	def ExecuteWaypointsPath(self, progress_callback):
		wpts = self.wpts
		print("Waypoints count:", len(wpts))
		self.robot.movel_waypoints(wpts)
		return

	def ExecuteSingleLinear(self, pt, a=0.2, v=0.2, wait=True):
		self.robot.movel(pt, a=a, v=v, wait=wait)
		return

	def ExecuteSingleLinearJoint(self, pt, a=0.75, v=0.5, wait=True):
		self.robot.movej(q=pt, a=a, v=v, wait=True)
		return

	def draw_waypoints_worker(self):
		worker = Worker(self.ExecuteWaypointsPath) # Any other args, kwargs are passed to the run function
		worker.signals.result.connect(self.print_result)
		worker.signals.finished.connect(self.draw_waypoints_thread_complete)
		worker.signals.progress.connect(self.ui.progress_fn)
		# Execute
		self.ui.threadpool.start(worker)

	def print_result(self, result):
		print("%s" % (result))

	def draw_waypoints_thread_complete(self):
		print("–––––––––––––––––––––––––––––")
		print("RESET to init cropped sizing:")
		self.constructDrawingCanvas()
		self.calculateCroppedSizing(self.ui.canvasH, self.ui.canvasW)
		# Exacute contemplate animation

	def playAnimation(self, animationPose):
		canvasH = self.ui.canvasH
		canvasW = self.ui.canvasW
		tabletData = False
		initTargetPose = 0

		if(len(animationPose[0]) == 3):
			tabletData = True

		if tabletData is True:
			[initX,initY, hover] = animationPose[0]
			poseIn3D = self.PixelTranslation(initX, initY, canvasH, canvasW)
			# initTargetPose = [poseIn3D[0], poseIn3D[1], poseIn3D[2], 0,3.14,0]

			# self.ExecuteSingleLinear(initTargetPose)
			self.ExecuteSingleLinearJoint(self.initTargetDrawPose, a=0.2, v=0.4)

			self.robot.init_realtime_control_pose()
		else:
			initTargetPose = animationPose[0]
			self.ExecuteSingleLinearJoint(initTargetPose)
			self.robot.init_realtime_control_joint()

		for pose in animationPose:
			time.sleep(0.185)
			if(self.ui.isAnimationPlaying == False):
				return "Interrupted"
			if(tabletData):
				penPressure = pose[2]
				coord = self.PixelTranslation(pose[0], pose[1], canvasH, canvasW)
				z = -coord[2] + self.zOffset
				if penPressure < 15:
					z = -coord[2] + 0.04
				self.robot.set_realtime_pose([coord[0], coord[1], z, 0,3.14,0])
			else:
				self.ui.osc_client.send_message("/wek/inputs", pose)
				self.robot.set_realtime_joint(pose)
		return "Animation Done."

