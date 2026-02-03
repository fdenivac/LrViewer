# -*- encoding: utf-8 -*-
# pylint: disable=too-many-lines,disable=line-too-long,invalid-name

"""

Lightroom Model for Photos

"""

from __future__ import annotations
import logging

from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    QRect,
    QSize,
)

from PySide6.QtWidgets import (
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QStyle,
)
from PySide6.QtGui import (
    QPainter,
    QPixmap,
    QGuiApplication,
    QColor,
)

from lrApi import lr_api
from thumbProvider import thumbs_provider


CELL_PADDING = 0
TEXT_HEIGHT = 20

# logger
log = logging.getLogger(__name__)


class ThumbDelegate(QStyledItemDelegate):
    """
    delegate for PhotosThumbView (QTableView):
    painting thumbnail + text in column 0
    """

    def __init__(self, cell_size, parent):
        super().__init__(parent)
        self.cell_size = cell_size

        self.color_cur: QColor = QGuiApplication.palette().highlight().color()
        self.color_sel = QColor(self.color_cur)
        self.color_sel.setAlpha(160)

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        """paint cell"""
        painter.save()
        # option.rect holds the area we are painting on the widget (a cell)
        if option.state & QStyle.StateFlag.State_Selected:
            pixmap = QPixmap(option.rect.width(), option.rect.height())
            index_cur = self.parent().currentIndex()
            color = self.color_cur if index.row() == index_cur.row() else self.color_sel
            pixmap.fill(color)
            painter.drawPixmap(option.rect, pixmap)

        # draw image
        #
        pixmap = None
        col_id = lr_api.column_index("id")
        if col_id >= 0:
            photo_id = lr_api.query_result(index.row(), col_id, visible_col=False)
            pixmap = thumbs_provider.get_thumb(photo_id, level="3")
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    option.rect.width(),
                    option.rect.height() - TEXT_HEIGHT,
                    aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
                )
        else:
            pixmap = QPixmap()
        if not pixmap.isNull():
            # Position in the middle of the area.
            size = pixmap.size()
            adjust_top = (option.rect.height() - TEXT_HEIGHT - size.height()) // 2
            adjust_left = (option.rect.height() - size.width()) // 2
            pixRect = QRect(
                option.rect.left() + adjust_left,
                option.rect.top() + adjust_top,
                size.width(),
                size.height(),
            )
            painter.drawPixmap(pixRect, pixmap)

        # Draw the title below the image
        col_id = lr_api.column_index("name")
        if col_id >= 0:
            text = lr_api.query_result(index.row(), col_id, visible_col=False)
            txt_rect = QRect(
                option.rect.x(),
                option.rect.y() + option.rect.height() - TEXT_HEIGHT,
                option.rect.width(),
                TEXT_HEIGHT,
            )
            painter.drawText(
                txt_rect,
                Qt.AlignmentFlag.AlignCenter,
                text,
            )

        painter.restore()

    def sizeHint(
        self,
        options: QStyleOptionViewItem,  # pylint: disable=unused-argument
        index: QModelIndex,  # pylint: disable=unused-argument
    ):
        """sizeHint define cell size : all items has same size"""
        return QSize(self.cell_size, self.cell_size)


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
            pixmap = thumbs_provider.get_thumb(row[col_id], level="0")
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


class PhotosModel(QAbstractTableModel):
    """
    Model for Lightroom Photos List
    """

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        """display header datas (override)"""
        if orientation == Qt.Orientation.Horizontal:
            if role == Qt.ItemDataRole.DisplayRole:
                try:
                    return lr_api.column(section, visible_col=True)
                except IndexError as _e:
                    log.info("failed headerData(%s)", section)
            if role == Qt.ItemDataRole.InitialSortOrderRole:
                return Qt.SortOrder.DescendingOrder
        if (
            orientation == Qt.Orientation.Vertical
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return f"{section + 1}"

    def data(self, index, role):
        """get data for role from index (override)"""
        log.debug("index = %s,%s", index.row(), index.column())
        if role == Qt.ItemDataRole.DisplayRole:
            # return formated data
            try:
                return lr_api.query_result(
                    index.row(), index.column(), visible_col=True
                )
            except IndexError:
                log.error("failed read row")
                return

        if role == Qt.ItemDataRole.UserRole:
            # return raw data
            try:
                return lr_api.query_result(
                    index.row(), index.column(), visible_col=True, raw=True
                )
            except IndexError:
                log.error("failed read row")
                return

    def index(
        self,
        row: int,
        column: int,
        parent: QModelIndex = QModelIndex(),  # pylint: disable=unused-argument
    ) -> QModelIndex:
        """create index for row, column (override)"""
        if row >= lr_api.query_count() or column >= lr_api.columns_count(
            visible_col=True
        ):
            log.debug("invalid photo index %s,%s", row, column)
            return QModelIndex()
        log.debug("create photo index %s,%s", row, column)
        return self.createIndex(row, column)

    def columnCount(self, index):  # pylint: disable=unused-argument
        """return column count (override)"""
        log.debug("column count = %s", lr_api.columns_count(visible_col=True))
        return lr_api.columns_count(visible_col=True)

    def rowCount(self, index):  # pylint: disable=unused-argument
        """return row count (override)"""
        log.debug("row count = %s", lr_api.query_count())
        return lr_api.query_count()


class LrSortFilterProxyModel(QSortFilterProxyModel):
    """
    Implements QSortFilterProxyModel for sorting views

    Not good idea with many an many rows ! consider using SQL order
    """

    def __init__(self, parent=None):
        super(LrSortFilterProxyModel, self).__init__(parent=parent)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        """override QSortFilterProxyModel.lessThan"""
        val_left = left.model().data(left, Qt.ItemDataRole.UserRole)
        val_right = left.model().data(right, Qt.ItemDataRole.UserRole)
        if val_left is None or val_right is None:
            if val_left is None and val_right:
                return False
            if (val_left or val_left is None) and val_right is None:
                return True
        return val_left < val_right
