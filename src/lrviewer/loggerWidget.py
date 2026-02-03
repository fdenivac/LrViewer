# -*- encoding: utf-8 -*-
# pylint: disable=line-too-long,invalid-name
"""
Logging widget

    Usage
        ...
        self.logTextBox = LoggerWidget(self)
        logging.getLogger().addHandler(self.logTextBox)
        logging.getLogger().setLevel(logging.DEBUG)
        ...
"""

import logging
from PySide6.QtCore import (
    Signal,
)
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QFileDialog,
)
from PySide6.QtGui import (
    QAction,
    QCursor,
)


class LoggerWidget(QPlainTextEdit, logging.Handler):
    """Logger widget"""

    appendText = Signal(str)

    def __init__(self, parent):
        super(LoggerWidget, self).__init__(parent)
        self.setReadOnly(True)
        self.setFormatter(
            logging.Formatter(
                "%(name)s - %(asctime)s.%(msecs)d - %(levelname)s - %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        self.appendText.connect(self.appendPlainText)

    def emit(self, record):
        msg = self.format(record)
        self.appendText.emit(msg)

    def contextMenuEvent(self, e):
        """add action to context menu (override)"""

        menu = self.createStandardContextMenu()

        menu.addSeparator()
        action = QAction("Clear Log ...", self)
        menu.addAction(action)
        action.triggered.connect(self.onClearLog)

        action = QAction("Save Log on disk ...", self)
        menu.addAction(action)
        action.triggered.connect(self.onSaveLog)

        menu.exec(QCursor.pos())

    def onSaveLog(self):
        """save log in file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Log", "", "Log Files (*.log);;All files (*.*)"
        )
        if not filename:
            return
        self.toPlainText()
        with open(filename, "w", encoding="utf8") as f:
            f.write(self.toPlainText())

    def onClearLog(self):
        """clear log window"""
        self.clear()
