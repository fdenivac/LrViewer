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
    QRect,
)
from PySide6.QtWidgets import (
    QWidget,
    QGridLayout,
    QHBoxLayout,
    QVBoxLayout,
)
from PySide6.QtGui import (
    QPixmap,
    QResizeEvent,
)

from .graphicsView import SingleImageGraphicsView
from .svgbutton import QSvgButtonIcon

log = logging.getLogger(__name__)


STYLE_SLIDESHOW = """
QWidget {
    background: transparent; 
}

SingleImageGraphicsView {
    border: none; 
    background: transparent; 
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
    play = Signal()
    pause = Signal()
    doubleClicked = Signal()
    exitFullscreen = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(STYLE_SLIDESHOW)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._interval = 6000

        self._initUi()

    def _initUi(self):
        self._view = SingleImageGraphicsView()
        self._view.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.installEventFilter(self)

        self._btnWidget = QWidget()

        self._prevBtn = self._create_nav_button("arrow-left.svg")
        self._prevBtn.clicked.connect(self._prev)

        self._nextBtn = self._create_nav_button("arrow-right.svg")
        self._nextBtn.clicked.connect(self._nextClicked)

        self._playBtn = self._create_nav_button("play.svg")
        self._playBtn.clicked.connect(self._playClicked)

        self._pauseBtn = self._create_nav_button("pause.svg")
        self._pauseBtn.clicked.connect(self._pauseClicked)

        lay_nav = QVBoxLayout()

        lay = QHBoxLayout()
        lay.addWidget(
            QWidget(geometry=QRect(0, 0, 100, 100)),
            alignment=Qt.AlignmentFlag.AlignLeft,
        )
        lay_nav.addLayout(lay)

        lay = QHBoxLayout()
        lay.addWidget(self._prevBtn, alignment=Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self._nextBtn, alignment=Qt.AlignmentFlag.AlignRight)
        lay_nav.addLayout(lay)

        lay = QVBoxLayout()
        lay.addWidget(self._playBtn, alignment=Qt.AlignmentFlag.AlignCenter)
        lay_nav.addLayout(lay)

        self._navWidget = QWidget()
        self._navWidget.setLayout(lay_nav)

        lay = QGridLayout()
        lay.addWidget(self._view, 0, 0, 3, 1)
        lay.addWidget(self._navWidget, 0, 0, 3, 1)
        lay.addWidget(self._btnWidget, 2, 0, 1, 1, Qt.AlignmentFlag.AlignCenter)
        self.setLayout(lay)

        self._timer = QTimer(self)
        self._timer.setInterval(self._interval)
        self._timer.timeout.connect(self._nextByTimer)
        self._timer.stop()

    def _create_nav_button(self, icon_path: str) -> QSvgButtonIcon:
        """Create a navigation button with SVG icon"""
        btn = QSvgButtonIcon(
            os.path.join(os.path.realpath(os.path.dirname(__file__)), icon_path)
        )
        btn.setObjectName("svgWidget")
        btn.setSvgSize(100, 100)
        btn.setEnabled(True)
        return btn

    def keyPressEvent(self, event):
        """process keys arrow left/right"""
        if event.key() == Qt.Key.Key_Left:
            self.previous.emit()
            return True
        if event.key() == Qt.Key.Key_Right:
            self.next.emit(False)
            return True
        if event.key() == Qt.Key.Key_Escape:
            self.exitFullscreen.emit()
            return True
        if event.key() == Qt.Key.Key_Space:
            if self._timer.isActive():
                self.pause.emit()
            else:
                self.play.emit()
            return True
        return super().keyPressEvent(event)

    def event(self, event):
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self.doubleClicked.emit()
            return True
        return super().event(event)

    def _prev(self):
        """click button previous"""
        self.previous.emit()

    def _nextByTimer(self):
        """next by timer"""
        log.info("Timer signal")
        self.next.emit(False)

    def _nextClicked(self):
        """click button next"""
        self.next.emit(True)

    def _playClicked(self):
        """click button play"""
        self.play.emit()

    def _pauseClicked(self):
        """click button pause"""
        self.pause.emit()

    def setInterval(self, milliseconds: int):
        """change timer value"""
        self._interval = milliseconds
        self._timer.setInterval(milliseconds)

    def getInterval(self) -> int:
        """get timer value"""
        return self._interval

    def setPhoto(self, photo: QPixmap):
        """set photo"""
        self._view.setImage(photo)

    def setNavigationButtonVisible(self, f: bool):
        """hide navigation widget"""
        self._navWidget.setVisible(f)

    def setBottomButtonVisible(self, f: bool):
        """hide buttons widget"""
        self._btnWidget.setVisible(f)

    def startSlideshow(self, f: bool):
        """start/stop timer and toggle play/pause icon in layout"""
        if f:
            self._timer.start()
            log.info("play")
            # remove play icon
            if self._playBtn.parent() == self._navWidget:
                self._navWidget.layout().removeWidget(self._playBtn)
                self._playBtn.setParent(None)
            self._playBtn.setVisible(False)
            # insert pause icon
            if self._pauseBtn.parent() != self._navWidget:
                self._navWidget.layout().addWidget(
                    self._pauseBtn, alignment=Qt.AlignmentFlag.AlignCenter
                )
            self._pauseBtn.setVisible(True)

        else:
            self._timer.stop()
            log.info("pause")
            # remove pause icon
            if self._pauseBtn.parent() == self._navWidget:
                self._navWidget.layout().removeWidget(self._pauseBtn)
                self._pauseBtn.setParent(None)
            self._pauseBtn.setVisible(False)
            # insert play icon
            if self._playBtn.parent() != self._navWidget:
                self._navWidget.layout().addWidget(
                    self._playBtn, alignment=Qt.AlignmentFlag.AlignCenter
                )
            self._playBtn.setVisible(True)

    def isSlideshowActive(self):
        """return True if Slideshow running"""
        return self._timer.isActive()

    def getBtnWidget(self):
        """get the btn widget

        to set the spacing (currently) :
            self._btnWidget.layout().setSpacing(5)
        """
        return self._btnWidget

    def getPrevBtn(self):
        """get the prev button"""
        return self._prevBtn

    def getNextBtn(self):
        """get the next button"""
        return self._nextBtn

    def resizeEvent(self, event: QResizeEvent):
        """event resize window"""
        ratio = min(event.size().width() / 1600, event.size().height() / 1600)
        self._prevBtn.setSvgSize(int(BT_SIZE_REF * ratio), int(BT_SIZE_REF * ratio))
        self._nextBtn.setSvgSize(int(BT_SIZE_REF * ratio), int(BT_SIZE_REF * ratio))
