from pyqtgraph.opengl import GLGraphicsItem
from pyqtgraph.Qt import QtCore, QtGui


class GL2DTextItem(GLGraphicsItem.GLGraphicsItem):
    def __init__(self, font_size=11, **kwds):
        super().__init__(**kwds)
        self.text = ""
        self.font_size = font_size

    def paint(self):
        self.setupGLState()

        painter = QtGui.QPainter(self.view())
        font = painter.font()
        font.setPixelSize(self.font_size)
        painter.setFont(font)
        self.draw(painter)
        painter.end()

    def draw(self, painter):
        painter.setPen(QtCore.Qt.GlobalColor.white)
        painter.setRenderHints(QtGui.QPainter.RenderHint.Antialiasing | QtGui.QPainter.RenderHint.TextAntialiasing)

        rect = self.view().rect()
        af = QtCore.Qt.AlignmentFlag

        painter.drawText(rect, af.AlignTop | af.AlignLeft, self.text)
