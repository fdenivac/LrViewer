# -*- encoding: utf-8 -*-
# pylint: disable=invalid-name,line-too-long

"""
Lightroom Photos List View
"""

from __future__ import annotations
import logging

from PySide6.QtWidgets import (
    QTableView,
    QAbstractItemView,
    QHeaderView,
    QFrame,
)
from PySide6.QtCore import (
    Qt,
    QModelIndex,
    QItemSelectionModel,
    QEvent,
)
from PySide6.QtGui import (
    QKeyEvent,
    QMouseEvent,
    QFontMetrics,
    QResizeEvent,
)

from modelPhotos import (
    PhotosModel,
    ThumbTextDelegate,
    LrSortFilterProxyModel,
)

# logger
log = logging.getLogger(__name__)

# sort and filter model
USE_SORT_LIST_MODEL = False

# height of photos list rows : (without_thumbnail, with_thumbnail)
#   the with_thumbnail value is also the thumbnail resized
PHOTOSLIST_ROW_HEIGHT = (30, 60)


PREFERRED_SIZE = {
    "name": 30,
    "name=full": 80,
    "name=base": 20,
    "name=basext": 25,
    "folder": 50,
    "id": 8,
    "uuid": 38,
    "rating": 4,
    "colorlabel": 8,
    "flag": 6,
    "datemod": 19,
    "datehist": 19,
    "datecapt": 19,
    "modcount": 2,
    "master": 10,
    "vname": 10,
    "stackpos": 3,
    "keywords": 30,
    "collections": 30,
    "camera": 15,
    "camerasn": 8,
    "lens": 20,
    "iso": 5,
    "focal": 6,
    "aperture": 6,
    "speed": 6,
    "flash": 4,
    "monochrome": 4,
    "creator": 18,
    "caption": 30,
    "dims": 10,
    "pubcollection": 30,
    "pubname": 30,
    "pubtime": 19,
    "latitude": 15,
    "longitude": 15,
    "duration": 5,
    "country": 10,
    "state": 10,
    "city": 10,
    "location": 10,
}


class PhotosListView(QTableView):
    """
    Lightroom Photos List Model
    """

    def __init__(self, model: PhotosModel):
        """Init Custom model"""
        super().__init__()

        if USE_SORT_LIST_MODEL:
            self.proxyModel = LrSortFilterProxyModel()
            self.proxyModel.setSourceModel(model)
            self.setModel(self.proxyModel)
        else:
            self.setModel(model)

        self.setFrameStyle(QFrame.Shape.NoFrame)

        self.setShowGrid(True)

        self.setSortingEnabled(True)
        self.horizontalHeader().setSortIndicatorShown(True)
        # no columns sorted :
        self.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)

        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setHighlightSections(True)

        self.delegate = ThumbTextDelegate(self)
        self.setItemDelegateForColumn(0, self.delegate)

        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.setAlternatingRowColors(True)

        self.last_header = []

    def useThumbs(self, show: bool):
        """set/unset use of thumbs in first column"""
        height_nothumb, height_thumb = PHOTOSLIST_ROW_HEIGHT
        if show:
            self.verticalHeader().setDefaultSectionSize(height_thumb)
        else:
            self.verticalHeader().setDefaultSectionSize(height_nothumb)
        self.delegate.setShowThumbs(show)

    def columnName(self, column_index: int):
        """return column name from index"""
        return self.model().headerData(
            column_index, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
        )

    def defaultColumnWidth(self, column_index: int):
        """return default column size from index"""
        font = self.font()
        metrics = QFontMetrics(font)
        col_name = self.columnName(column_index)
        if col_name in PREFERRED_SIZE:
            width = PREFERRED_SIZE[col_name] * metrics.averageCharWidth()
            return width
        log.warning("no size for %s", col_name)
        return 10 * metrics.averageCharWidth()

    def resizeColumnsToWindow(self, fit: bool = False):
        """
        resize columns to fit window
        """
        if not self.isVisible():
            return
        column_count = self.horizontalHeader().count()
        last_header = [self.columnName(icol) for icol in range(0, column_count)]
        if not fit and last_header == self.last_header:
            # log.info("same header")
            return
        self.last_header = last_header

        # compute default size
        default_total_width = 0
        default_widths = []
        for icol in range(0, column_count):
            width = self.defaultColumnWidth(icol)
            default_total_width += width
            default_widths.append(width)

        # column width larger than windows : it's OK
        window_width = self.width() - (
            self.verticalHeader().width() + self.verticalScrollBar().width() + 5
        )
        if not fit and default_total_width > window_width:
            for icol in range(0, column_count):
                self.setColumnWidth(icol, default_widths[icol])
            return

        # distribute left width on all column with ratio
        computed_total_width = 0
        computed_widths = []
        ratio = window_width / default_total_width
        for icol in range(0, column_count):
            width = round(default_widths[icol] * ratio)
            computed_total_width += width
            computed_widths.append(width)
            self.setColumnWidth(icol, width)

    def selectionCommand(self, index: QModelIndex, /, event: QEvent = ...):
        """selection command override"""
        if event is not None:
            if event.type() == event.Type.MouseButtonPress:
                event: QMouseEvent = event
                if event.button() == Qt.MouseButton.LeftButton:
                    if self.selectionModel().isSelected(index):
                        return (
                            QItemSelectionModel.SelectionFlag.Current
                            | QItemSelectionModel.SelectionFlag.Rows
                        )
                    return (
                        QItemSelectionModel.SelectionFlag.Clear
                        | QItemSelectionModel.SelectionFlag.SelectCurrent
                        | QItemSelectionModel.SelectionFlag.Rows
                    )
        return super().selectionCommand(index, event)

    def keyPressEvent(self, event: QKeyEvent):
        """KeyPressEvent override for navigate in selection"""
        if event.key() in [Qt.Key.Key_Up, Qt.Key.Key_Down]:
            selModel = self.selectionModel()
            sel = selModel.selectedRows(0)
            if len(sel) > 1:
                curRow = selModel.currentIndex().row()
                idRows = sorted([s.row() for s in sel])
                try:
                    id_next = idRows.index(curRow)
                except ValueError:
                    log.error("key row no next/prev")
                    super().keyPressEvent(event)
                    event.ignore()
                    return super().keyPressEvent(event)
                if event.key() == Qt.Key.Key_Down:
                    id_next = (id_next + 1) % len(idRows)
                else:
                    id_next = (id_next - 1) % len(idRows)
                index = self.model().createIndex(idRows[id_next], 0)
                selModel.setCurrentIndex(
                    index, QItemSelectionModel.SelectionFlag.Select
                )
                return
        return super().keyPressEvent(event)

    def resizeEvent(self, event: QResizeEvent):
        """window resize event: use proportion"""
        if event.oldSize().width() == -1:
            self.resizeColumnsToWindow()
            return
        column_count = self.horizontalHeader().count()
        ratio = event.size().width() / event.oldSize().width()
        computed_total_width = 0
        for icol in range(0, column_count):
            width = round(self.columnWidth(icol) * ratio)
            computed_total_width += width
            self.setColumnWidth(icol, width)
