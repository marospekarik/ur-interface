from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import sys, traceback
from scipy.interpolate import interp1d
from Utils import figureOrientation
class WindowDraw(QWidget):
    """
    This "window" is a QWidget. If it has no parent,
    it will appear as a free-floating window.
    """

    def __init__(self, mainWindow, app):
        super().__init__()
        # Tablet
        self.pen_is_down = False
        self.pen_x = mainWindow.canvasW/2
        self.pen_y = mainWindow.canvasH/2
        self.pen_pressure = 0
        self.text = ""
        layout = QVBoxLayout()
        # Resizing the sample window to full desktop size:
        #frame_rect = app.desktop().frameGeometry()
        # TODO: RESIZE FULL SCREEN WITH NO CLOSE BUTTON!
        #frame_rect = self.frameGeometry()
        frame_rect = app.desktop().frameGeometry()
        width, height = frame_rect.width(), frame_rect.height()
        self.resize(width, height)
        self.move(-9, 0)
        self.setLayout(layout)
        self.mainWindow = mainWindow

    def tabletEvent(self, tabletEvent):
        #https://docs.huihoo.com/pyqt/pyqt/html/qtabletevent.html
        if self.mainWindow.activated:
            pen_x = tabletEvent.globalX()
            pen_y = tabletEvent.globalY()

            #Re-map the tablet resolution
            mX = interp1d([0,2560],[0,self.mainWindow.canvasW])
            mY = interp1d([0,1440],[0,self.mainWindow.canvasH])

            x =  mX(pen_x)
            y = mY(pen_y)
            newPoint = figureOrientation([x,y],self.mainWindow.canvasW, self.mainWindow.canvasH, 0, 0, 1)

            self.pen_x = newPoint[0]
            self.pen_y = newPoint[1]

            self.pen_pressure = int(tabletEvent.pressure() * 100)
            if tabletEvent.type() == QTabletEvent.TabletPress:
                self.pen_is_down = True
                self.text = "TabletPress event"
            elif tabletEvent.type() == QTabletEvent.TabletMove:
                self.pen_is_down = True
                self.text = "TabletMove event"
            elif tabletEvent.type() == QTabletEvent.TabletRelease:
                self.pen_is_down = False
                self.text = "TabletRelease event"
            self.text += " at x={0}, y={1}, pressure={2}%,".format(self.pen_x, self.pen_y, self.pen_pressure)
            if self.pen_is_down:
                self.text += " Pen is down."
            else:
                self.text += " Pen is up."
            
            #self.mainWindow.tabletPos = f"X: {self.pen_x} | Y: {self.pen_y}"
            coord = self.mainWindow.myRobot.PixelTranslation(self.pen_x, self.pen_y, self.mainWindow.canvasH, self.mainWindow.canvasW)
            z = -coord[2] + self.mainWindow.myRobot.zOffset
            if self.pen_pressure < 15:
                z = -coord[2] + 0.04
            self.mainWindow.myRobot.robot.set_realtime_pose([coord[0], coord[1], z, 0,3.14,0])
        else: 
            print("not activated")

        tabletEvent.accept()
        self.update()
        
    
    def paintEvent(self, event):
        text = self.text
        i = text.find("\n\n")
        if i >= 0:
            text = text.left(i)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)
        painter.drawText(self.rect(), Qt.AlignTop | Qt.AlignLeft , text)