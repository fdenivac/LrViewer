# -*- encoding: utf-8 -*-
# pylint: disable=too-many-lines,disable=line-too-long,invalid-name

"""
Collections Widget

Collections are :
    - Lightroom (regular) collections (photos list)
    - Lightroom Smart collections (criteria)
    - Lightroom Folders
    - Lightroom Keywords
    - Lightroom Published collections
    - lrtools Queries

This widget contains :
    - tree view collections (CollectionsView)
    - line edit for filter collection (QLineEdit)

The widget is populated in model(CollectionsModel) initialization via the global Lrtools API (PhotosAPI) instance

TODO : diacritics insensitive

"""
from __future__ import annotations
import logging


from PySide6.QtWidgets import (
    QAbstractItemView,
    QWidget,
    QLineEdit,
    QVBoxLayout,
)
from PySide6.QtCore import (
    Qt,
    QSortFilterProxyModel,
)


from modelCollections import CollectionsModel
from treeViewCollections import CollectionsView

log = logging.getLogger(__name__)


class SearchProxyModel(QSortFilterProxyModel):
    """Collection filter"""

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """filter rows"""
        text = (
            self.sourceModel()
            .index(sourceRow, 0, sourceParent)
            .data(Qt.ItemDataRole.DisplayRole)
        )
        return self.filterRegularExpression().match(text).hasMatch()


class CollectionsFilterWidget(QWidget):
    """
    CollectionsFilterWidget embedding TreeViewCollections and QLineEdit :
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.resize(300, 500)

        # filter control
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter...")

        # init model
        self.model = SearchProxyModel()
        self.model.setSourceModel(CollectionsModel())
        self.model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.model.setRecursiveFilteringEnabled(True)
        self.model.setSortLocaleAware(False)

        self.collections = CollectionsView(self.model)
        self.collections.setSortingEnabled(False)
        self.collections.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed)
        self.collections.setHeaderHidden(True)
        self.collections.setUniformRowHeights(True)

        # layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.filter)
        main_layout.addWidget(self.collections)
        self.setLayout(main_layout)

        # signals
        self.filter.textChanged.connect(self.filter_changed)

        # expose methods from self.collections
        self.clicked = self.collections.clicked
        self.selectCollection = self.collections.selectCollection
        self.queryUnstored = self.collections.queryUnstored
        self.onLoadQueries = self.collections.onLoadQueries
        self.loadQueries = self.collections.loadQueries
        self.onSaveQueries = self.collections.onSaveQueries
        self.onStoreQuery = self.collections.onStoreQuery
        self.isQueriesModified = self.collections.isQueriesModified
        self.currentQueryIndex = self.collections.currentQueryIndex
        self.expand_siblings = self.collections.expand_siblings
        self.setModel = self.model.setSourceModel
        self.selectionModel = self.collections.selectionModel
        self.clearSelection = self.collections.clearSelection

    def filter_changed(self, text=None):
        """textChanged in filter"""
        self.model.setFilterFixedString(text)

    #
    # expose methods from collections
    #

    def indexFromPath(self, path):
        """indexFromPath for modelCollections"""
        return self.model.mapFromSource(self.model.sourceModel().indexFromPath(path))

    def pathToItem(self, path, case=True):
        """pathToItem for modelCollections"""
        return self.model.sourceModel().pathToItem(path, case)

    def absolutePath(self, index):
        """absolutePath for collections"""
        index = self.model.mapToSource(index)
        return self.model.sourceModel().absolutePath(index)

    def itemType(self, index):
        """itemType for collection"""
        index = self.model.mapToSource(index)
        return self.model.sourceModel().itemType(index)

    def createQuery(self):
        """Create Query"""
        index = self.collections.currentQueryIndex()
        if not index.isValid():
            # get query root index
            index = self.indexFromPath("Query:/")
            index = self.model.mapToSource(index)
        self.collections.onCreateQuery(None, index)

    def createQueryCollection(self):
        """create query collection"""
        index = self.collections.currentQueryIndex()
        if not index.isValid():
            # get query root index
            index = self.indexFromPath("Query:/")
            index = self.model.mapToSource(index)
        self.collections.onCreateQueryCollection(None, index)

    def renameQuery(self):
        """rename active query"""
        index = self.collections.currentQueryIndex()
        if not index.isValid():
            return
        self.collections.onRenameQuery(None, index)

    def removeQuery(self):
        """remove active query"""
        index = self.collections.currentQueryIndex()
        if not index.isValid():
            return
        self.collections.onRemoveQuery(None, index)
