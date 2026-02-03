# pylint: disable=invalid-name
"""
SingleImageGraphicsView

modified from "https://github.com/yjg30737/pyqt-slideshow"

"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView


class SingleImageGraphicsView(QGraphicsView):
    """GraphicsView"""

    def __init__(self):
        super().__init__()
        self.__aspectRatioMode = Qt.AspectRatioMode.KeepAspectRatio
        self._scene = QGraphicsScene()
        self._p = QPixmap()
        self._item = ""

    def setImage(self, image: QPixmap):
        """set image pixmap"""
        if image is None:
            image = QPixmap()
        self._p = image
        self._scene = QGraphicsScene()
        self._item = self._scene.addPixmap(self._p)

        self.setScene(self._scene)
        self.fitInView(self._item, self.__aspectRatioMode)

    def setAspectRatioMode(self, mode):
        """set aspect ratio"""
        self.__aspectRatioMode = mode

    def resizeEvent(self, e):
        """resize window"""
        if self._item:
            self.fitInView(self.sceneRect(), self.__aspectRatioMode)
        return super().resizeEvent(e)
