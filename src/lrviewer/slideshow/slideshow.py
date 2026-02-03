# pylint: disable=too-many-lines,line-too-long,invalid-name

"""
Slideshow widget

modified from "https://github.com/yjg30737/pyqt-slideshow"
"""
import os
import logging

from PySide6.QtCore import (
    Qt,
    QTimer,
    QEvent,
    Signal,
)
from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QHBoxLayout,
)
from PySide6.QtGui import (
    QPixmap,
    QResizeEvent,
)

from .graphicsView import SingleImageGraphicsView
from .svgbutton import QSvgButtonIcon


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


STYLE_SLIDESHOW = """
QWidget {
    background: transparent; border: 0px;
}
QSvgButtonIcon {
    padding:  5px;
    padding-left: 20px;
    padding-right: 20px;
    border: 0px solid transparent;
    color: #00FFFF00;
}

QSvgButtonIcon:hover {
    padding:  5px;
    padding-left: 20px;
    padding-right: 20px;
    color: #804163A6;

}
QSvgButtonIcon:pressed {
    padding:  5px;
    padding-left: 10px;
    padding-right: 10px;
    color: #804163A6;
}
"""

BT_SIZE_REF = 300


class SlideShow(QWidget):
    """
    Widget slideshow
        - passive component :
            send signal on click next/previous, timer
    """

    previous = Signal()
    next = Signal(bool)
    doubleClicked = Signal()

    def __init__(self, parent=None, flags=Qt.WindowType.Widget):
        """init forcing Window Type (seems mandatory for set full screen mode)"""
        super().__init__(parent, flags)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setStyleSheet(STYLE_SLIDESHOW)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.__interval = 6000
        self.__initUi()

    def __initUi(self):
        self.__view = SingleImageGraphicsView()
        self.__view.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.__view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.__view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.__view.setStyleSheet("QGraphicsView { background: black; border: 0px; }")
        self.__view.installEventFilter(self)

        self.__btnWidget = QWidget()

        self.__prevBtn = QSvgButtonIcon(
            os.path.join(os.path.realpath(os.path.dirname(__file__)), "arrow-left.svg")
        )
        self.__prevBtn.setObjectName("svgWidget")
        self.__prevBtn.setSvgSize(100, 100)
        self.__prevBtn.clicked.connect(self.__prev)
        self.__prevBtn.setEnabled(True)

        self.__nextBtn = QSvgButtonIcon(
            os.path.join(os.path.realpath(os.path.dirname(__file__)), "arrow-right.svg")
        )
        self.__nextBtn.setObjectName("svgWidget")
        self.__nextBtn.setSvgSize(100, 100)
        self.__nextBtn.clicked.connect(self.__nextClicked)
        self.__nextBtn.setEnabled(True)

        lay = QHBoxLayout()
        lay.addWidget(self.__prevBtn, alignment=Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self.__nextBtn, alignment=Qt.AlignmentFlag.AlignRight)

        self.__navWidget = QWidget()
        self.__navWidget.setLayout(lay)

        lay = QGridLayout()
        lay.addWidget(self.__view, 0, 0, 3, 1)
        lay.addWidget(self.__navWidget, 0, 0, 3, 1)
        lay.addWidget(self.__btnWidget, 2, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)
        self.setLayout(lay)

        self.__timer = QTimer(self)
        self.__timer.setInterval(self.__interval)
        self.__timer.timeout.connect(self.__nextByTimer)
        self.__timer.stop()

    def keyPressEvent(self, event):
        """process keys arrow left/right"""
        if event.key() == Qt.Key.Key_Left:
            self.previous.emit()
            return True
        elif event.key() == Qt.Key.Key_Right:
            self.next.emit(False)
            return True
        return super().keyPressEvent(event)

    def event(self, event):
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self.doubleClicked.emit()
            return True
        return super().event(event)

    def __prev(self):
        """click button previous"""
        self.previous.emit()

    def __nextByTimer(self):
        """next by timer"""
        log.info("Timer signal")
        self.next.emit(False)

    def __nextClicked(self):
        """click button next"""
        self.next.emit(True)

    def setInterval(self, milliseconds: int):
        """change timer value"""
        self.__interval = milliseconds
        self.__timer.setInterval(milliseconds)

    def getInterval(self) -> int:
        """get timer value"""
        return self.__interval

    def setPhoto(self, photo: QPixmap):
        """set photo"""
        self.__view.setImage(photo)

    def setNavigationButtonVisible(self, f: bool):
        """hide navigation widget"""
        self.__navWidget.setVisible(f)

    def setBottomButtonVisible(self, f: bool):
        """hide buttons widget"""
        self.__btnWidget.setVisible(f)

    def setTimerEnabled(self, f: bool):
        """start/stop timer"""
        if f:
            self.__timer.start()
        else:
            self.__timer.stop()

    def isTimerActive(self):
        """return True if Slideshow running"""
        return self.__timer.isActive()

    def getBtnWidget(self):
        """get the btn widget

        to set the spacing (currently) :
            self.__btnWidget.layout().setSpacing(5)
        """
        return self.__btnWidget

    def getPrevBtn(self):
        """get the prev button"""
        return self.__prevBtn

    def getNextBtn(self):
        """get the next button"""
        return self.__nextBtn

    def resizeEvent(self, event: QResizeEvent):
        """event resize window"""
        ratio = min(event.size().width() / 1600, event.size().height() / 1600)
        self.__prevBtn.setSvgSize(int(BT_SIZE_REF * ratio), int(BT_SIZE_REF * ratio))
        self.__nextBtn.setSvgSize(int(BT_SIZE_REF * ratio), int(BT_SIZE_REF * ratio))
