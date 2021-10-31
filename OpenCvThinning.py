import math, numpy as np
import cv2
# READ THIS! Don't forget to install contrib version of openCV:
# pip install opencv-contrib-python

# def auto_canny(image, sigma=0.33):
# 	# compute the median of the single channel pixel intensities
# 	v = np.median(image)
# 	# apply automatic Canny edge detection using the computed median
# 	lower = int(max(0, (1.0 - sigma) * v))
# 	upper = int(min(255, (1.0 + sigma) * v))
# 	edged = cv2.Canny(image, lower, upper)
# 	# return the edged image
# 	return edged

image = cv2.imread("abs.png")
print(image.shape, image.dtype, image.min(), image.max(), image.mean(), image.std(), image.sum())
gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
thinned = cv2.ximgproc.thinning(gray, cv2.ximgproc.THINNING_GUOHALL)

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
