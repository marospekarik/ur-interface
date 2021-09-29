import numpy as np
import argparse
import cv2

image = cv2.imread("IP.jpg")
#Remember, boundaries are stored as BGR, not RGB

#Stroke
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