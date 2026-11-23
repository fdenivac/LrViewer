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
)
from lrApi import lr_api

# logger
log = logging.getLogger(__name__)


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
        # log.debug("index = %s,%s", index.row(), index.column())
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

    def columnCount(self, index):  # pylint: disable=unused-argument
        """return column count (override)"""
        # log.debug("column count = %s", lr_api.columns_count(visible_col=True))
        return lr_api.columns_count(visible_col=True)

    def rowCount(self, index):  # pylint: disable=unused-argument
        """return row count (override)"""
        # log.debug("row count = %s", lr_api.query_count())
        return lr_api.query_count()

    def thumbChanged(self, index):
        """send signal dataChanged"""
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole])


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
