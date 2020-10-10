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