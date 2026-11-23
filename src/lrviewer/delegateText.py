# -*- encoding: utf-8 -*-
# pylint: disable=too-many-lines,disable=line-too-long,invalid-name

"""

Lightroom Model for Photos

"""

from __future__ import annotations
import logging

from PySide6.QtCore import (
    Qt,
    QModelIndex,
    QRect,
)

from PySide6.QtWidgets import (
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QStyle,
)
from PySide6.QtGui import (
    QPainter,
    QGuiApplication,
    QColor,
)

# from settings import settings
from lrApi import lr_api
from thumbProvider import thumbs_provider

CELL_PADDING = 0
TEXT_HEIGHT = 20

# logger
log = logging.getLogger(__name__)


class ThumbTextDelegate(QStyledItemDelegate):
    """
    delegate for PhotosListView (QListView):
    painting thumbnail + text in column 0
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.showThumbs = False
        self.color_cur: QColor = QGuiApplication.palette().highlight().color()
        self.color_sel = QColor(self.color_cur)
        self.color_sel.setAlpha(160)

    def setShowThumbs(self, show: bool):
        """set/unset thumbs in first column"""
        self.showThumbs = show

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        """paint"""

        if option.state & QStyle.StateFlag.State_Selected:
            index_cur = self.parent().currentIndex()
            color = self.color_cur if index.row() == index_cur.row() else self.color_sel
            painter.fillRect(option.rect, color)

        if index.column() != 0:
            assert False  # thumb is always in firt column
        try:
            data = lr_api.query_result(index.row(), index.column(), visible_col=True)
        except IndexError:
            log.error("failed read row")
            return

        if not self.showThumbs:
            painter.save()
            painter.setBrush(option.backgroundBrush)
            textRect = option.rect
            textRect.setLeft(textRect.left() + 5)
            painter.drawText(option.rect, option.displayAlignment, str(data))
            painter.restore()
            return

        pixmap = None
        col_id = lr_api.column_index("id")
        if col_id >= 0:
            row = lr_api.query_results[index.row()]
            pixmap = thumbs_provider.get_thumb(row[col_id], level="0", source=index)
            if not pixmap.isNull():
                size = option.rect.height() - 2
                pixmap = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio)

        painter.save()
        if pixmap:
            size = pixmap.size()
            adjust_top = (option.rect.height() - size.height()) // 2
            adjust_left = (option.rect.height() - size.width()) // 2
            pixRect = QRect(
                option.rect.left() + adjust_left,
                option.rect.top() + adjust_top,
                size.width(),
                size.height(),
            )
            painter.drawPixmap(pixRect, pixmap)
        textRect = QRect(option.rect)
        textRect.setLeft(option.rect.left() + option.rect.height() + 5)
        painter.drawText(textRect, option.displayAlignment, str(data))
        painter.restore()
