# -*- encoding: utf-8 -*-
# pylint: disable=too-many-lines,disable=line-too-long,invalid-name,attribute-defined-outside-init


"""

Some Qt functions

"""

import typing

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
)


def getMainWindow() -> typing.Union[QMainWindow, None]:
    """Find the QMainWindow in application"""
    app = QApplication.instance()
    for widget in app.topLevelWidgets():
        if isinstance(widget, QMainWindow):
            return widget
    return None
