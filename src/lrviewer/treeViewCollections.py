# -*- encoding: utf-8 -*-
# pylint: disable=too-many-lines,disable=line-too-long,invalid-name

"""
Collections Tree View

Collections are :
    - Lightroom (regular) collections (photos list)
    - Lightroom Smart collections (criteria)
    - Lightroom Folders
    - Lightroom Keywords
    - lrtools Queries

"""

from __future__ import annotations
import os
import logging
import json

from PySide6.QtWidgets import (
    QTreeView,
    QFrame,
    QMenu,
    QMessageBox,
    QFileDialog,
    QAbstractItemView,
    QInputDialog,
)
from PySide6.QtCore import (
    Qt,
    QModelIndex,
    Signal,
)
from PySide6.QtGui import QCursor, QAction

from qtutils import getMainWindow
from lrApi import lr_api
from settings import settings
from modelCollections import CollectionsModel, TreeItem, ItemType
from uiDialogs import QueryDialog


log = logging.getLogger(__name__)


class CollectionsView(QTreeView):
    """
    Lightroom Sets Tree View
    """

    selectCollection = Signal(QModelIndex)
    queryUnstored = Signal(str, str)

    def __init__(self, model: CollectionsModel):
        """Init Custom model"""
        QTreeView.__init__(self)
        self.setModel(model)
        self.setHeaderHidden(True)
        self.setFrameStyle(QFrame.Shape.NoFrame)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.onContextMenu)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

        self.uniformRowHeights = True

        self.clicked.connect(self.on_click)
        self.expanded.connect(self.on_expanded)
        self.collapsed.connect(self.on_collapsed)

        # queries modifs detection
        self.model().dataChanged.connect(self.onDataChanged)
        self.model().sourceModel().treeChanged.connect(self.onTreeChanged)

        root_index = self.model().index(0, 0)
        self.expand_siblings(root_index)

        self._queriesModified = False

    def on_click(self, index):
        """click on collection"""
        log.info("Click on collection")
        index = self.model().mapToSource(index)
        self.selectCollection.emit(index)

    def on_expanded(self, index):
        """on expand collection : scroll center"""
        self.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
        self.resizeColumnToContents(0)

    def on_collapsed(self, _):
        """on on_pressed : resize contents"""
        self.resizeColumnToContents(0)

    def keyPressEvent(self, event):
        """key pressed on collection"""
        if event.key() == Qt.Key.Key_Return:
            log.info("keyPressEvent(Key_RETURN)")
            index = self.currentIndex()
            index = self.model().mapToSource(index)
            self.selectCollection.emit(index)
        else:
            super().keyPressEvent(event)

    def onContextMenu(self, position):
        """create context"""
        index0 = self.indexAt(position)
        if not index0.isValid():
            return
        menu = QMenu()
        index = self.model().mapToSource(index0)
        item: TreeItem = index.internalPointer()
        if item.itemType() in [
            ItemType.LRTOOLS_QUERY,
            ItemType.LRTOOLS_COLLECTION_QUERY,
            ItemType.LRTOOLS_QUERY_ROOT,
        ]:
            action = QAction("Create Query ...", self)
            action.triggered.connect(lambda checked: self.onCreateQuery(checked, index))
            menu.addAction(action)

            action = QAction("Create Query Collection ...", self)
            action.triggered.connect(
                lambda checked: self.onCreateQueryCollection(checked, index)
            )
            menu.addAction(action)

            action = QAction("Rename/Edit Query ...", self)
            action.setStatusTip("Rename this stored query")
            action.triggered.connect(lambda checked: self.onRenameQuery(checked, index))
            menu.addAction(action)
            action.setEnabled(
                item.itemType()
                in [ItemType.LRTOOLS_COLLECTION_QUERY, ItemType.LRTOOLS_QUERY]
            )

            action = QAction("Remove Query", self)
            action.setStatusTip("Remove this stored query")
            action.triggered.connect(lambda checked: self.onRemoveQuery(checked, index))
            action.setEnabled(
                item.itemType()
                in [ItemType.LRTOOLS_COLLECTION_QUERY, ItemType.LRTOOLS_QUERY]
            )
            menu.addAction(action)

        if menu.actions():
            menu.addSeparator()
        action = QAction("Expand from here", self)
        action.triggered.connect(lambda expand, id=index0: self.onExpandRecursively(id))
        if not item.child_count():
            action.setEnabled(False)
        menu.addAction(action)

        menu.exec(QCursor.pos())

    def onExpandRecursively(self, index):
        """expand all children"""
        self.setUpdatesEnabled(False)
        self.expandRecursively(index, -1)
        self.setUpdatesEnabled(True)

    def expand_siblings(self, root_index=None):
        """
        Expands/collapses all the children and grand children etc. of index.
        """
        if root_index is None:
            root_index = self.model().index(0, 0)
        col = 0
        while True:
            index = self.model().sibling(col, 0, root_index)
            if not index.isValid():
                break
            self.expand(index)
            col += 1
        return

    def currentQueryIndex(self):
        """return current active index"""
        index = self.currentIndex()
        index = self.model().mapToSource(index)
        if not index.isValid():
            return index
        if index.internalPointer().itemType() not in [
            ItemType.LRTOOLS_QUERY,
            ItemType.LRTOOLS_COLLECTION_QUERY,
        ]:
            return QModelIndex()
        return index

    def onSaveQueries(self, _):
        """save queries on disk"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Queries", "", "Query Files (*.lrtq);;All files (*.*)"
        )
        if not filename:
            return
        model = self.model().sourceModel()
        json_str = json.dumps(model.toJson(QModelIndex()), indent=4)
        with open(filename, "w", encoding="utf8") as f:
            f.write(json_str)
        self._queriesModified = False

    def onLoadQueries(self, _, merge=False):
        """load queries"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Queries", "", "Query Files (*.lrtq);;All files (*.*)"
        )
        if not filename:
            return
        self.loadQueries(filename, merge)
        settings.setValue("LastQueryFile", filename)

    def loadQueries(self, filename, merge=False):
        """load queries filename"""
        if not merge:
            model: CollectionsModel = self.model().sourceModel()
            index = model.indexFromPath("Query:/")
            item: TreeItem = index.internalPointer()
            model.removeRows(0, item.child_count(), index)
        try:
            with open(filename, encoding="utf8") as f:
                queries = json.load(f)
            model: CollectionsModel = self.model().sourceModel()
            model.fromJson("", queries)
        except (json.decoder.JSONDecodeError, KeyError):
            QMessageBox.critical(self, "Error", f"Invalid queries file ({filename})")
            return
        except FileNotFoundError as _e:
            QMessageBox.critical(self, "Error", f"Failed to open ({filename})\n{_e}")
            return
        index = model.indexFromPath("Query:")
        log.info("Load queries in : %s", model.data(index, Qt.ItemDataRole.DisplayRole))
        self.expand(self.model().mapFromSource(index))
        self.scrollTo(
            self.model().mapFromSource(index),
            QAbstractItemView.ScrollHint.PositionAtCenter,
        )
        self._queriesModified = merge

    def onRemoveQuery(self, _, index: QModelIndex):
        """remove item at given index"""
        log.info("remove query")
        coll_name = index.data(Qt.ItemDataRole.DisplayRole)
        ret = QMessageBox.question(
            self,
            "Remove Query",
            f'Do you confirm remove "{coll_name}" ?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        log.info("remove query")
        model = self.model().sourceModel()
        model.removeRows(index.row(), 1, model.parent(index))
        self._queriesModified = True

    def onRenameQuery(self, _, index: QModelIndex):
        """rename item"""
        assert index.isValid()
        model: CollectionsModel = self.model().sourceModel()
        if model.itemType(index) == ItemType.LRTOOLS_QUERY:
            query, columns = model.userData(index)
        else:
            query = columns = ""
        dialog = QueryDialog(model.data(index, 0), query, columns, self)
        if model.itemType(index) == ItemType.LRTOOLS_COLLECTION_QUERY:
            dialog.ui.query.setEnabled(False)
            dialog.ui.columns.setEnabled(False)
            dialog.setWindowTitle("Edit Query Collection")
        if not dialog.exec():
            return
        log.info("rename query")
        model.setData(index, dialog.ui.queryName.text(), Qt.ItemDataRole.EditRole)
        model.setUserData(index, (dialog.ui.query.text(), dialog.ui.columns.text()))
        self.selectCollection.emit(index)
        self._queriesModified = True

    def onCreateQuery(self, _, index: QModelIndex):
        """create query item"""
        if not index.isValid():
            return
        model: CollectionsModel = self.model().sourceModel()
        item: TreeItem = index.internalPointer()
        # unique name for query
        query_name = self._suggest_name("New Query", item, inQuery=True)
        query = columns = None
        while True:
            dialog = QueryDialog(
                query_name, lr_api.criteria(), lr_api.columns(visible_col=True), self
            )
            if not dialog.exec():
                return
            if not dialog.ui.queryName.text():
                # no query name => query not stored, but signal emited for execution by main view
                self.queryUnstored.emit(
                    dialog.ui.query.text(), dialog.ui.columns.text()
                )
                log.info("query unstored emit")
                return
            # check if name exists in level
            if self._is_unique_name(dialog.ui.queryName.text(), item, inQuery=True):
                query_name = dialog.ui.queryName.text()
                query, columns = dialog.ui.query.text(), dialog.ui.columns.text()
                break
            getMainWindow().statusBar().showMessage(
                "Query name must be unique in branch", 3000
            )

        getMainWindow().statusBar().clearMessage()

        if model.itemType(index) in [
            ItemType.LRTOOLS_COLLECTION_QUERY,
            ItemType.LRTOOLS_QUERY_ROOT,
        ]:
            index_new = model.append_child_item(
                index,
                query_name,
                (query, columns),
                ItemType.LRTOOLS_QUERY,
            )
            self.expand(self.model().mapFromSource(index))
        else:
            index_new = model.insert_item(
                index.parent(),
                index.row(),
                query_name,
                (query, columns),
                ItemType.LRTOOLS_QUERY,
            )
        log.info(
            "create new query : %s", model.data(index_new, Qt.ItemDataRole.DisplayRole)
        )
        self.scrollTo(
            self.model().mapFromSource(index_new),
            QAbstractItemView.ScrollHint.PositionAtCenter,
        )
        self.selectCollection.emit(index_new)
        self._queriesModified = True

    def onStoreQuery(self):
        """
        store current query in collection panel
        """
        # suggestion unique name
        model: CollectionsModel = self.model().sourceModel()
        base_name = "Query:/New Query"
        name = base_name
        num = 1
        while True:
            index = model.indexFromPath(name)
            if not index.isValid():
                break
            num += 1
            name = f"{base_name} {num}"

        # dialog until unique name
        fpath = query = columns = None
        while True:
            dialog = QueryDialog(
                os.path.basename(name),
                lr_api.criteria(),
                lr_api.columns(visible_col=True),
                self,
            )
            if not dialog.exec():
                return
            # check unique name
            fpath = f"Query:/{dialog.ui.queryName.text().strip()}"
            index = model.indexFromPath(fpath)
            if not index.isValid():
                query, columns = dialog.ui.query.text(), dialog.ui.columns.text()
                break
            self.statusBar().showMessage('Name must be in "Query:" root section', 3000)

        index = model.createFromPath(fpath, (query, columns), ItemType.LRTOOLS_QUERY)
        self.expand(self.model().mapFromSource(index.parent()))
        self.scrollTo(
            self.model().mapFromSource(index),
            QAbstractItemView.ScrollHint.PositionAtCenter,
        )
        self._queriesModified = True

    def onCreateQueryCollection(self, _, index: QModelIndex):
        """create query collection item"""
        if not index.isValid():
            return
        log.info("create collection (%s,%s)", index.row(), index.column())
        item: TreeItem = index.internalPointer()
        model: CollectionsModel = self.model().sourceModel()

        # unique name for collection
        coll_name = self._suggest_name("New Collection", item, inQuery=False)
        while True:
            coll_name, ok = QInputDialog.getText(
                self, "Create New Collection", "Name:", text=coll_name
            )
            if not ok:
                return
            # check if name exists in level
            if self._is_unique_name(coll_name, item, inQuery=False):
                break
            coll_name = self._suggest_name("New Collection", item, inQuery=False)
            getMainWindow().statusBar().showMessage(
                "Query Collection name must be unique in branch", 3000
            )

        if model.itemType(index) in [
            ItemType.LRTOOLS_COLLECTION_QUERY,
            ItemType.LRTOOLS_QUERY_ROOT,
        ]:
            index_new = model.append_child_item(
                index,
                coll_name,
                None,
                ItemType.LRTOOLS_COLLECTION_QUERY,
            )
        else:
            index_new = model.insert_item(
                index.parent(),
                index.row(),
                coll_name,
                ("", ""),
                ItemType.LRTOOLS_COLLECTION_QUERY,
            )

        self.expand(self.model().mapFromSource(index_new.parent()))
        self.scrollTo(
            self.model().mapFromSource(index_new),
            QAbstractItemView.ScrollHint.PositionAtCenter,
        )
        log.info(
            "create new query collection : %s",
            model.data(index_new, Qt.ItemDataRole.DisplayRole),
        )
        self._queriesModified = True

    def onDataChanged(
        self, top_left: QModelIndex, bottom_right: QModelIndex, roles
    ):  # pylint: disable=unused-argument
        """item data changed

        An item has been renamed : only queries can be renamed, so mark as modified"""
        self._queriesModified = True

    def onTreeChanged(self):
        """signal dropped from model : marks queries as modified"""
        self._queriesModified = True

    def isQueriesModified(self):
        """return True id queries modified"""
        return self._queriesModified

    def _is_unique_name(self, name: str, item: TreeItem, inQuery: bool) -> bool:
        """(internal) return True if name is unique in children"""
        root = (
            item
            if item.itemType()
            in [ItemType.LRTOOLS_COLLECTION_QUERY, ItemType.LRTOOLS_QUERY_ROOT]
            else item.parent()
        )
        for child in root.child_items:
            if inQuery and child.itemType() != ItemType.LRTOOLS_QUERY:
                continue
            if not inQuery and child.itemType() != ItemType.LRTOOLS_COLLECTION_QUERY:
                continue
            if child.item_data[0] == name:
                return False
        return True

    def _suggest_name(self, base_name: str, item: TreeItem, inQuery: bool):
        """(internal) propose unique name for query or collection"""
        name = base_name
        num = 1
        while True:
            if self._is_unique_name(name, item, inQuery):
                return name
            num += 1
            name = f"{base_name} {num}"
