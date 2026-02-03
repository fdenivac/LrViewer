# -*- encoding: utf-8 -*-
# pylint: disable=invalid-name,line-too-long

"""

Photo Thumbs View

"""
import logging

from PySide6.QtWidgets import (
    QAbstractItemView,
    QListView,
)
from PySide6.QtCore import (
    Qt,
    QModelIndex,
    QItemSelectionModel,
    QEvent,
    QSize,
)
from PySide6.QtGui import (
    QKeyEvent,
)

from modelPhotos import (
    PhotosModel,
    ThumbDelegate,
    LrSortFilterProxyModel,
)


# logger
log = logging.getLogger(__name__)

# use sort and filter model
USE_SORT_LIST_MODEL = False


class PhotosThumbView(QListView):
    """
    main explorer in icon mode
    """

    def __init__(self, model: PhotosModel):
        super().__init__()

        if USE_SORT_LIST_MODEL:
            self.proxyModel = LrSortFilterProxyModel()
            self.proxyModel.setSourceModel(model)
            self.setModel(self.proxyModel)
        else:
            self.setModel(model)

        self.setViewMode(QListView.ViewMode.IconMode)
        self.setWordWrap(True)

        grid_size = 180
        cell_size = 178

        self.setGridSize(QSize(grid_size, grid_size))

        self.delegate = ThumbDelegate(cell_size, self)
        self.setItemDelegateForColumn(0, self.delegate)

        self.setUniformItemSizes(True)

        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.setStyleSheet("QListView { margin: auto;}")

    def selectionCommand(self, index: QModelIndex, /, event: QEvent = ...):
        """selection command override"""
        if event is not None:
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    if self.selectionModel().isSelected(index):
                        return (
                            QItemSelectionModel.SelectionFlag.Current
                            | QItemSelectionModel.SelectionFlag.Rows
                        )
                    if event.modifiers() != Qt.KeyboardModifier.ControlModifier:
                        return (
                            QItemSelectionModel.SelectionFlag.Clear
                            | QItemSelectionModel.SelectionFlag.SelectCurrent
                            | QItemSelectionModel.SelectionFlag.Rows
                        )
        return super().selectionCommand(index, event)

    def keyPressEvent(self, event: QKeyEvent):
        """KeyPressEvent override for navigate in selection"""
        if event.key() in [
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
        ]:
            selModel = self.selectionModel()
            sel = selModel.selectedRows(0)
            if len(sel) > 1:
                curRow = selModel.currentIndex().row()
                idRows = sorted([s.row() for s in sel])
                try:
                    id_next = idRows.index(curRow)
                except ValueError:
                    log.error("key row no next/prev")
                    event.ignore()
                    return super().keyPressEvent(event)
                if event.key() == Qt.Key.Key_Right:
                    id_next = (id_next + 1) % len(idRows)
                elif event.key() == Qt.Key.Key_Left:
                    id_next = (id_next - 1) % len(idRows)
                elif event.key() == Qt.Key.Key_Down:
                    id_next = (id_next + self.computeIconsPerLine()) % len(idRows)
                # elif event.key() == Qt.Key.Key_Up:
                else:
                    id_next = (id_next - self.computeIconsPerLine()) % len(idRows)
                index = self.model().createIndex(idRows[id_next], 0)
                selModel.setCurrentIndex(
                    index, QItemSelectionModel.SelectionFlag.Select
                )
                return
        return super().keyPressEvent(event)

    def computeIconsPerLine(self):
        """return icons number per line"""
        view_width = self.viewport().width()
        grid_width = self.gridSize().width()
        icons = view_width // grid_width
        print(icons)
        return icons
