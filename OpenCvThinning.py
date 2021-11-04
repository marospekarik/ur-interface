import math, numpy as np
import cv2
import Utils
import json

# READ THIS! Don't forget to install contrib version of openCV:
# pip install opencv-contrib-python

def GetCurrentFrame():
	cv2.namedWindow("preview")
	vc = cv2.VideoCapture(1)
	i = 0
	if vc.isOpened(): # try to get the first frame
		rval, frame = vc.read()
	else:
		rval = False

	while rval:
		i+=1
		# cv2.imshow("preview", frame)
		rval, frame = vc.read()
		if i == 10:
			# cv2.imshow("cap", frame)
			# cv2.waitKey(0)
			break
		key = cv2.waitKey(20)
		if key == 27: # exit on ESC
			break

	# cv2.destroyWindow("preview")
	# cv2.destroyWindow("cap")
	cv2.imshow("frame", frame)
	cv2.waitKey(0)
	return frame


def CalibrateHomography():
	im_src = GetCurrentFrame()
	[h, w, t] = im_src.shape
    # Destination image
	size = (w,h,t)
	im_dst = np.zeros(size, np.uint8)
	pts_dst = np.array(
					[
					[0,0],
					[size[0] - 1, 0],
					[size[0] - 1, size[1] -1],
					[0, size[1] - 1 ]
					], dtype=float
					)

	# Show image and wait for 4 clicks.
	cv2.imshow("Calibrate LeftTop to Right", im_src)
	pts_src = Utils.get_four_points(im_src)
	print("Homography Points:", pts_src)
	# Calculate the homography
	h, status = cv2.findHomography(pts_src, pts_dst)

	# Warp source image to destination
	im_dst = cv2.warpPerspective(im_src, h, size[0:2])

	# Show output
	cv2.imshow("Image", im_dst)
	# cv2.waitKey(0)
	key = cv2.waitKey(0)
	if key == 27: # exit on ESC
		return
	if key == 13: # save on 'enter'
		cv2.imwrite("background.jpg", im_dst)
		with open('./data/homography.json', 'w') as outfile:
			json.dump({'points': pts_src.tolist()}, outfile)

def GetCurrentPerspectiveFrame():
	im_src = GetCurrentFrame()
	pts_src = 0
	# Maybe rework to local state
	with open('./data/homography.json') as json_file:
		homography = json.load(json_file)
		pts_src = np.array(homography.get('points'))
		print(pts_src)
	[h, w, t] = im_src.shape

	size = (w,h,t)
	im_dst = np.zeros(size, np.uint8)
	pts_dst = np.array(
					[
					[0,0],
					[size[0] - 1, 0],
					[size[0] - 1, size[1] -1],
					[0, size[1] - 1 ]
					], dtype=float
					)
	h, status = cv2.findHomography(pts_src, pts_dst)
	im_dst = cv2.warpPerspective(im_src, h, size[0:2])
	cv2.imshow("im_dst", im_dst)
	cv2.waitKey(0)
	return im_dst


def BackgroundSubtraction():
	frame = GetCurrentPerspectiveFrame()
	frameBg = cv2.imread("background.jpg")

	first_gray = cv2.cvtColor(frameBg, cv2.COLOR_BGR2GRAY)
	first_gray = cv2.GaussianBlur(first_gray, (21, 21), 0)

	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	gray = cv2.GaussianBlur(gray, (21, 21), 0)

	difference = cv2.absdiff(gray, first_gray)

	# Apply thresholding to eliminate noise
	thresh  = cv2.threshold(difference, 40, 255, cv2.THRESH_BINARY)[1]
	thresh = cv2.erode(thresh, None, iterations=2)
	thresh = cv2.dilate(thresh, None, iterations=2)


	# Transfer the thresholded image to the original image

	cv2.imshow("first_gray", first_gray)
	cv2.waitKey(0)
	cv2.imshow("gray", gray)
	cv2.waitKey(0)
	cv2.imshow("Thresh", thresh)

	cv2.waitKey(0)
	return thresh


def Thinning(image):
	# image = cv2.imread(img)
	# bg substraction
	# gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
	dst = cv2.GaussianBlur(image,(5,5),cv2.BORDER_DEFAULT)
	# inverted = cv2.bitwise_not(dst)
	thinned = cv2.ximgproc.thinning(dst, cv2.ximgproc.THINNING_GUOHALL)

	#  OLD COUNTOUR EXTRACTION DOWN THERE
	cnts, _ = cv2.findContours(thinned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	lstcont = []
	approx = []
	dist_thresh = 0
	ep_val= 0

	for c in cnts:
		# Simplify
		epsilon = ep_val * cv2.arcLength(c, False)
		approx.append(cv2.approxPolyDP(c, epsilon, False))

	for c in approx:
		isEmpty = True
		cont = []
		pv = c[0][0]
		for p in c:
			point = np.array([p[0, 0], p[0, 1]])
			# print point
			if math.sqrt((pv[0] - point[0]) * (pv[0] - point[0]) + (pv[1] - point[1]) * (
				pv[1] - point[1])) >= dist_thresh:
				cont.append(point)
				isEmpty = False
				pv = point
		if isEmpty == False:
			lstcont.append(cont)

	temp_img = cv2.cvtColor(thinned, cv2.COLOR_GRAY2BGR)
	c_i = 0
	cnt_index = 0
	for c in lstcont:
		cnt_index += 1
		# print(lstcont)
		# print('____________________________________________________________')
		# print(c)
		# print('____________________________________________________________')
		# pv = c
		isFirst = True
		for p in c:
			cn = (p[0], p[1])
			# print(cn)
			if isFirst == True:
				pv = cn
				isFirst = False
			# if euclidean_dist(pv, cn) > dist_thresh:
			if (c_i == 0):
				cv2.line(temp_img, pv, cn, color=(255, 0, 0), thickness=1)
			elif (c_i == 1):
				cv2.line(temp_img, pv, cn, color=(0, 255, 0), thickness=1)
			else:
				cv2.line(temp_img, pv, cn, color=(0, 0, 255), thickness=1)
			pv = cn

			c_i += 1
			if c_i >= 3:
				c_i = 0

	print (' contour count ', cnt_index)
	cv2.imshow("Contoured", temp_img)
	cv2.waitKey(0)

	return [lstcont, temp_img]

Thinning(BackgroundSubtraction())
