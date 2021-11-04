import cv2
import numpy as np

def figureOrientation(coord,canvasW, canvasH,rotation, mirrorW, mirrorH):
    # Mirror horizontal
    # Mirror vertical
    # Rotation (4 states)
    # Preasumin that canvas has been calibrated clockwise starting in the left bottom according to the human.
    # Being the canvasWith the edge closer to the robot and human independently the orientation of the paper.

    Xprim = coord[0]
    Yprim = coord[1]
    x = coord[0]
    y = coord[1]

    # Rotate 90 deg cunterclockwise
    if rotation == 1:
        y = canvasH - Xprim*canvasH/canvasW
        x = Yprim*canvasW/canvasH

    #
    if rotation == 2:
        y = canvasH - Yprim
        x = canvasW - Xprim

    if rotation == 3:
        y = Xprim*canvasH/canvasW
        x = canvasW - Yprim*canvasW/canvasH
    if mirrorH:
        y = canvasH - y
    if mirrorW:
        x = canvasW - x
    # Portrait format
    # x = int(val[1]) * (self.canvasW/self.canvasH)
    # y =  -int(val[0]) * (self.canvasH/self.canvasW) + self.canvasH
    # x = int(x)
    # y = int(y)


    x = int(x)
    y = int(y)
    return [x, y]

def mouse_handler(event, x, y, flags, data) :

    if event == cv2.EVENT_LBUTTONDOWN :
        cv2.circle(data['im'], (x,y),3, (0,0,255), 5, 16);
        cv2.imshow("Image", data['im']);
        if len(data['points']) < 4 :
            data['points'].append([x,y])

def get_four_points(im):

    # Set up data to send to mouse handler
    data = {}
    data['im'] = im.copy()
    data['points'] = []

    #Set the callback function for any mouse event
    cv2.imshow("Image",im)
    cv2.setMouseCallback("Image", mouse_handler, data)
    cv2.waitKey(0)

    # Convert array to np.array
    points = np.vstack(data['points']).astype(float)

    return points
