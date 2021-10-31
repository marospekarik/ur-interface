import cv2
import numpy as np
import argparse


def JamesContourAl1g(img, isTesting=False):
    '''try:
def ImageContoursCustomSet1(img, isTesting=False):
    try:
        cimg2 = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        gray = cv2.cvtColor(cimg2, cv2.COLOR_BGR2GRAY)
    except:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)'''
    retval, gray = cv2.threshold(img, 220, 255, cv2.THRESH_BINARY_INV)

    try:
        cnts, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    except:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = gray - 255
        cnts, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    gray = 255 - gray
    _, cnts, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    lstcont = []
    for i in cnts:
        cont = []
        for y in i:
            cont.append([y[0][0], y[0][1]])
        lstcont.append(cont)
    return lstcont


def ImageContoursCustomSet2(img, isTesting=False):
    try:
        cimg2 = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        gray = cv2.cvtColor(cimg2, cv2.COLOR_BGR2GRAY)
    except:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gray = 255 - gray
    cv2.imshow('', gray)
    cv2.waitKey(2020202)
    # _,cnts,_=cv2.findContours(gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cv2.findNonZero(gray)
    lstcont = []
    for i in cnts:
        lstcont.append([i[0, 0], i[0, 1]])
    return lstcont


def JamesContourAlgff(img):
    import math, numpy as np
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = gray - 255
    pts = np.array(np.nonzero(gray))
    lstcont = []
    while len(pts[0] > 0):
        lstcont.append([pts[1][0], pts[0][0]])
        pts.remove(pts[1][0])
        pts.remove(pts[0][0])
        print(lstcont)
    print(pts)
    return pts

def MarcusCountourAlg(image):
	image = cv2.imread(image)

	redlower = [102, 108, 155]
	redupper = [144, 140, 200]
	#greenlower = [48, 78, 46]
	#greenupper = [139, 163, 145]

	#Color Light
	#redlower = [82, 75, 165]
	#redupper = [102, 95, 200]
	#greenlower = [80, 139, 75]
	#greenupper = [116, 167, 130]
	#bluelower = [148, 140, 87]
	#blueupper = [171, 172, 143]
	#violetlower = [114, 83, 116]
	#violetupper = [149, 133, 164]

	#Color Dark
	#redlower = [70, 70, 144]
	#redupper = [112, 103, 186]
	#greenlower = [96, 134, 113]
	#greenupper = [131, 164, 152]
	#bluelower = [114, 97, 34]
	#blueupper = [157, 147, 98]

	openkernel = np.ones((11,11), np.uint8)
	closekernel = np.ones((3,3), np.uint8)
	horizontalkernel = np.array([
		[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
		[1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
		[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],], dtype = "uint8")
	verticalkernel = np.array([
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
		[0, 1, 0],
	])
	lower = np.array(redlower, dtype = "uint8")
	upper = np.array(redupper, dtype = "uint8")

	mask = cv2.inRange(image, lower, upper)

	result = cv2.dilate(mask, openkernel)
	result = cv2.erode(result, openkernel)
	#cv2.imshow("openresult", result)
	result = cv2.erode(result, closekernel)
	result = cv2.dilate(result, closekernel)

	horizontal = cv2.morphologyEx(result, cv2.MORPH_OPEN, horizontalkernel)
	horizontalrgb = cv2.cvtColor(horizontal,cv2.COLOR_GRAY2RGB)
	contours, hierarchy = cv2.findContours(horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	horizontalrgb = cv2.drawContours(horizontalrgb, contours, -1, (255,0,0), 2)

	finalx1 = [0] * 800
	finaly1 = [0] * 800
	finalx2 = [0] * 800
	finaly2 = [0] * 800

	for g in range(len(contours)):
		polygon_points = contours[g]
		best_pair = (-1, -1)
		longest_distance = -1
		n = len(polygon_points)
		for i in range(1, n):  # [1;n-1]  <-  all number from 1 (inclusive) to n (inclusive)
			for j in range(0, i):  # [0;i-1]
				p1 = polygon_points[i][0]
				p2 = polygon_points[j][0]
				x_diff = p2[0] - p1[0]
				y_diff = p2[1] - p1[1]
				distance = np.sqrt(x_diff**2 + y_diff**2)
				if distance > longest_distance:
					longest_distance = distance
					best_pair = (i, j)

		finalx1[g] = polygon_points[best_pair[0]][0][0]  # polygon_points -> start_node -> point -> x_coord
		finaly1[g] = polygon_points[best_pair[0]][0][1]  # polygon_points -> start_node -> point -> y_coord
		finalx2[g] = polygon_points[best_pair[1]][0][0]  # polygon_points -> end_node -> point -> x_coord
		finaly2[g] = polygon_points[best_pair[1]][0][1]  # polygon_points -> end_node -> point -> y_coord

	print(finalx1)
	for k in range(len(contours) + 1):
		#print("First point")
		#print(finalx1[k - 1])
		#print(finaly1[k - 1])
		#print("Second point")
		#print(finalx2[k - 1])
		#print(finaly2[k - 1])

		cv2.line(horizontalrgb, (finalx1[k - 1], finaly1[k - 1]), (finalx2[k - 1], finaly2[k - 1]), (0,255,0), thickness=2)

	cv2.imshow("horizontalrgb", horizontalrgb)
	cv2.imshow("horizontal", horizontal)
	cv2.imwrite('horizontalrgb.png', horizontalrgb)
	cv2.waitKey(0)

	# return [lstcont, temp_img]


def JamesContourAlg(img, ep_val=0, dist_thresh=0):
    import math, numpy as np
    # dist thesh == 14, ep_val == 0.0015
    # dist_thresh = 4
    # ep_val = 0.001
    retval, gray = cv2.threshold(img, 200, 255, cv2.THRESH_BINARY_INV)
    print('James contour code')
    #  cv2.imshow('',gray)
    # cv2.waitKey(200)
    # Code to find contours
    # print(gray.shape)
    # cnts, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    try:
        cnts, _ = cv2.findContours(gray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    except:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = gray - 255
        _, cnts, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # print ImageContoursCustomSet2(cv2.imread('/home/naodev/Documents/default_ROSws/src/ur10DrawingSocial/robot_img_v2/human_2.png'))

    '''
    def JamesContourAlg_TEST(img):
	    import math, numpy as np
	    # dist thesh == 14, ep_val == 0.0015
	    dist_thresh = 14  # 8 #14
	    ep_val = 0.00015
	    retval, gray = cv2.threshold(img, 220, 255, cv2.THRESH_BINARY_INV)
	    print('James contour code')
	    #  cv2.imshow('',gray)
	    # cv2.waitKey(200)
	    # Code to find contours
	    cnts, _ = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    '''
    lstcont = []
    approx = []

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

    temp_img = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
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


    # cv2.imshow('Results', temp_img)
    # cv2.waitKey(500)
    print (' contour count ', cnt_index)
    return [lstcont, temp_img]


'''
    c_i = 0
    for c in lstcont:
        # print(lstcont)
        print('____________________________________________________________')
        print(c)
        print('____________________________________________________________')
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

    cv2.imshow('Results', temp_img)
    cv2.waitKey(500)


    return lstcont
'''
