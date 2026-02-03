# -*- encoding: utf-8 -*-
# pylint: disable=too-many-lines,disable=line-too-long,invalid-name

"""
Lightroom Model for collections tree view

Here, collections are :
    - Lightroom (regular) collections (photos list)
    - Lightroom Smart collection (criteria)
    - Lightroom Folders
    - Lightroom Keywords

"""

from __future__ import annotations
import os
import logging
from pathlib import PurePosixPath
from enum import Enum
import pickle

from PySide6.QtGui import (
    QIcon,
)

from PySide6.QtCore import (
    Qt,
    QAbstractItemModel,
    QModelIndex,
    QMimeData,
    QByteArray,
    Signal,
    QObject,
)


from lrtools.lrkeyword import LRKeywords
from lrApi import lr_api


# logger
log = logging.getLogger(__name__)


class ItemType(Enum):
    """Item Types"""

    COLLECTION_REGULAR = 1
    COLLECTION_SMART = 2
    COLLECTION_GROUP = 3
    FOLDER = 4
    KEYWORD = 5
    LRTOOLS_QUERY = 6
    LRTOOLS_COLLECTION_QUERY = 7
    LRTOOLS_QUERY_ROOT = 8
    PUBLISH_SERVICE = 9
    PUBLISH_COLLECTION_GROUP = 10
    PUBLISH_COLLECTION = 11
    PUBLISH_COLLECTION_BUILTIN = 12


class TreeItem:
    """
    Lightroom item for various collections
    """

    def __init__(
        self,
        data: list,
        user_data: any = None,
        item_type: ItemType = None,
        parent: TreeItem = None,
    ):
        self.item_data = data
        self.internal_data = user_data
        self.item_type = item_type
        self.parent_item = parent
        self.child_items = []

    def child(self, number: int) -> TreeItem:
        """return child at given position"""
        if number < 0 or number >= len(self.child_items):
            return None
        return self.child_items[number]

    def last_child(self):
        """return last child"""
        return self.child_items[-1] if self.child_items else None

    def child_count(self) -> int:
        """return child count"""
        return len(self.child_items)

    def child_number(self) -> int:
        """return children number"""
        if self.parent_item:
            return self.parent_item.child_items.index(self)
        return 0

    def column_count(self) -> int:
        """return column count"""
        return len(self.item_data)

    def data(self, column: int):
        """return data in column"""
        if column < 0 or column >= len(self.item_data):
            return None
        return self.item_data[column]

    def insert_children(self, position: int, count: int, columns: int) -> bool:
        """insert children"""
        if position < 0 or position > len(self.child_items):
            return False

        for _ in range(count):
            data = [None] * columns
            item = TreeItem(data.copy(), None, None, self)
            self.child_items.insert(position, item)

        return True

    def insert_columns(self, position: int, columns: int) -> bool:
        """insert columns"""
        if position < 0 or position > len(self.item_data):
            return False

        for _ in range(columns):
            self.item_data.insert(position, None)

        for child in self.child_items:
            child.insert_columns(position, columns)

        return True

    def parent(self):
        """return parent"""
        return self.parent_item

    def remove_children(self, position: int, count: int) -> bool:
        """remove children"""
        if position < 0 or position + count > len(self.child_items):
            return False

        for _ in range(count):
            self.child_items.pop(position)

        return True

    def remove_columns(self, position: int, columns: int) -> bool:
        """remove columns"""
        if position < 0 or position + columns > len(self.item_data):
            return False

        for _ in range(columns):
            self.item_data.pop(position)

        for child in self.child_items:
            child.remove_columns(position, columns)

        return True

    def set_data(self, column: int, value):
        """set data"""
        if column < 0 or column >= len(self.item_data):
            return False

        self.item_data[column] = value
        return True

    def __repr__(self) -> str:
        result = f"<treeitem.TreeItem at 0x{id(self):x}"
        for d in self.item_data:
            result += f' "{d}"' if d else " <None>"
        result += f", {len(self.child_items)} children>"
        return result

    def add_child(self, child: TreeItem) -> None:
        """add child to item"""
        child.parent_item = self
        self.child_items.append(child)

    def row(self) -> int:
        """return item row"""
        if self.parent_item is None:
            return 0
        # (Warning list.index use __eq__)
        return self.parent_item.child_items.index(self)

    def find_child(self, name: str) -> TreeItem:
        """return child item 'name' in column 0"""
        for item in self.child_items:
            if item.item_data[0] == name:
                return item

    def copy_tree(self, item_src: TreeItem):
        """copy tree"""
        for src in item_src.child_items:
            child = TreeItem(src.item_data, src.internal_data, src.item_type, self)
            self.add_child(child)
            child.copy_tree(src)

    def absolutePath(self) -> str:
        """build full path"""
        parts = []
        item = self
        while not item.parent() is None:
            parts.append(item.data(0))
            item = item.parent()
        parts.reverse()
        return str(PurePosixPath("").joinpath(*parts))

    def itemType(self) -> ItemType:
        """return item type"""
        return self.item_type

    def userData(self) -> any:
        """return item type"""
        return self.internal_data

    def set_userData(self, userdata):
        """set user data (internal)"""
        self.internal_data = userdata


class CollectionsModel(QAbstractItemModel):
    """
    Collections Model
    """

    class Signals(QObject):
        """specific signals"""

        treeChanged = Signal()

    signals = Signals()

    def __init__(self, parent=None):

        def abspath(filename):
            return os.path.join(os.path.realpath(os.path.dirname(__file__)), filename)

        super().__init__(parent)

        # simplify writing
        self.treeChanged = CollectionsModel.signals.treeChanged

        self.thumbnail = False
        self.root_item = TreeItem(["ROOT"])

        # used on drag/drop for store a TreeItem
        self.__tmp_storage_cooky = 0
        self.__tmp_storage_dct = {}

        self.icons = {
            ItemType.COLLECTION_GROUP: QIcon(abspath("ico/folder_blue.png")),
            ItemType.COLLECTION_REGULAR: QIcon(abspath("ico/coll_blue.png")),
            ItemType.COLLECTION_SMART: QIcon(abspath("ico/coll_blue_smart.png")),
            ItemType.PUBLISH_SERVICE: QIcon(abspath("./ico/folder_violet.png")),
            ItemType.PUBLISH_COLLECTION_GROUP: QIcon(
                abspath("./ico/folder_violet.png")
            ),
            ItemType.PUBLISH_COLLECTION: QIcon(abspath("./ico/coll_violet.png")),
            ItemType.PUBLISH_COLLECTION_BUILTIN: QIcon(
                abspath("./ico/coll_violet.png")
            ),
            ItemType.FOLDER: QIcon(abspath("./ico/folder_yellow.png")),
            ItemType.KEYWORD: QIcon(abspath("./ico/collection_keyword.png")),
            ItemType.LRTOOLS_QUERY: QIcon(abspath("./ico/coll_green.png")),
            ItemType.LRTOOLS_COLLECTION_QUERY: QIcon(abspath("./ico/folder_green.png")),
            ItemType.LRTOOLS_QUERY_ROOT: QIcon(abspath("./ico/folder_green.png")),
        }

        if not lr_api.is_connected():
            return
        self.populate()

    def populate(self):
        """
        Populate tree with various collections
        """

        TYPE_LR_TO_COLLECTION = {
            "com.adobe.ag.library.collection": ItemType.COLLECTION_REGULAR,
            "com.adobe.ag.library.group": ItemType.COLLECTION_GROUP,
            "com.adobe.ag.library.smart_collection": ItemType.COLLECTION_SMART,
            "com.adobe.ag.export.service.connection": ItemType.PUBLISH_SERVICE,
            "com.adobe.ag.library.group.published": ItemType.PUBLISH_COLLECTION_GROUP,
            "com.adobe.ag.library.collection.published": ItemType.PUBLISH_COLLECTION,
            "com.adobe.ag.library.collection.published.built-in": ItemType.PUBLISH_COLLECTION_BUILTIN,
        }

        # populate Lightroom Collections
        colls = lr_api.api.hierarchical_collections()
        for coll_name, coll_id, coll_type in colls:
            item_type = TYPE_LR_TO_COLLECTION[coll_type]
            coll = f'Collections:/{"/".join(coll_name)}'
            self.createFromPath(coll, coll_id, item_type)

        # populate Lightroom Folders
        rows = lr_api.api.lrphoto.select_generic(
            "idfolder, folder", "videos=0, distinct"
        ).fetchall()
        for folder_id, folder_name in rows:
            folder_name = folder_name.replace(":", "", 1)
            folder = f"Folders:/{folder_name}"
            self.createFromPath(folder, folder_id, ItemType.FOLDER)

        # populate Lightroom Keywords
        lrkeys = LRKeywords(lr_api.api)
        keywords = lrkeys.get_hierarchical_list()
        for key_name in keywords:
            key_id = lrkeys.get_id(key_name)
            key_name = "Keywords:/" + key_name.replace("|", "/")
            self.createFromPath(key_name, key_id, ItemType.KEYWORD)

        # populate Lightroom Published Collections
        colls = lr_api.api.hierarchical_published_collections()
        for coll_name, coll_id, coll_type in colls:
            item_type = TYPE_LR_TO_COLLECTION[coll_type]
            coll = f'Published:/{"/".join(coll_name)}'
            self.createFromPath(coll, coll_id, item_type)

        # populate lrtools Queries
        self.createFromPath("Query:/", (None, None), ItemType.LRTOOLS_QUERY_ROOT)

    def rootItem(self):
        """return tree root item"""
        return self.root_item

    def columnCount(
        self, parent: QModelIndex = None  # pylint: disable=unused-argument
    ) -> int:
        """Return row count from parent index (override)"""
        return self.root_item.column_count()

    def data(self, index: QModelIndex, role: int = None):
        """return data from index (override)"""
        if not index.isValid():
            return None

        item: TreeItem = self.get_item(index)

        if role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            return item.data(index.column())

        elif role == Qt.ItemDataRole.DecorationRole:
            if index.column() == 0:
                if item.item_type is not None:
                    return self.icons[item.item_type]

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """return flags for index (override)"""

        if not index.isValid():
            return QAbstractItemModel.flags(self, index)

        item: TreeItem = index.internalPointer()
        if item.itemType() not in [
            ItemType.LRTOOLS_QUERY,
            ItemType.LRTOOLS_COLLECTION_QUERY,
            ItemType.LRTOOLS_QUERY_ROOT,
        ]:
            return QAbstractItemModel.flags(self, index)

        if item.itemType() == ItemType.LRTOOLS_QUERY_ROOT:
            return Qt.ItemFlag.ItemIsDropEnabled | QAbstractItemModel.flags(self, index)

        return (
            Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsDragEnabled
            | Qt.ItemFlag.ItemIsDropEnabled
            | QAbstractItemModel.flags(self, index)
        )

    def supportedDragActions(self):
        """return supported drag actions (override)"""
        return Qt.DropAction.MoveAction

    def supportedDropActions(self) -> Qt.DropAction:
        """return supported drop actions (override)"""
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list:
        """return allowed mime types (override)"""
        return ["text/plain", "lrviewer/item"]

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        """return encoded data in QMimeData (override)"""
        log.info("mimeData for %s indexes", len(indexes))

        mime_data = QMimeData()
        text_data = item_data = []
        for index in indexes:
            item: TreeItem = index.internalPointer()
            criteria = columns = None
            if not item.internal_data is None:
                criteria, columns = item.internal_data
            text_data.append(
                f"{item.item_data[0]}||{criteria}||{columns}||{item.item_type.value}"
            )
            item_data.append(index)
        assert len(indexes) == 1
        mime_data.setText(text_data[0])

        # encode item
        self.__tmp_storage_dct = {self.__tmp_storage_cooky: item}
        mime_data.setData(
            "lrviewer/item", QByteArray(pickle.dumps(self.__tmp_storage_cooky))
        )
        self.__tmp_storage_cooky += 1

        return mime_data

    def dropMimeData(
        self,
        mime_data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        """drop data on item (override)"""
        item: TreeItem = parent.internalPointer()
        if item is None:
            log.info("drop data on None item ! (%s,%s)", row, column)
            return False
        log.info(
            "drop action:%s data: %s on (%s,%s), parent=%s",
            action,
            mime_data.text(),
            row,
            column,
            item.item_data,
        )
        name, criteria, columns, item_type = mime_data.text().split("||")
        if row == -1 and column == -1:
            # drop on item
            if item.item_type == ItemType.LRTOOLS_QUERY:
                log.info("drop forbiden on query")
                return False
            if ItemType(int(item_type)) == ItemType.LRTOOLS_COLLECTION_QUERY:
                cooky = pickle.loads(mime_data.data("lrviewer/item").data())
                item_src = self.__tmp_storage_dct.pop(cooky)
                index_dest = self.append_child_item(
                    parent, name, (criteria, columns), ItemType(int(item_type))
                )
                item_dest = index_dest.internalPointer()
                item_dest.copy_tree(item_src)
                self.treeChanged.emit()
                return True
            self.append_child_item(
                parent, name, (criteria, columns), ItemType(int(item_type))
            )
            self.treeChanged.emit()
            return True
        # drop before or after item
        if ItemType(int(item_type)) == ItemType.LRTOOLS_COLLECTION_QUERY:
            log.info("drop collection")
            cooky = pickle.loads(mime_data.data("lrviewer/item").data())
            item_src = self.__tmp_storage_dct.pop(cooky)
            index_dest = self.insert_item(
                parent, row, name, (criteria, columns), ItemType(int(item_type))
            )
            item_dest = index_dest.internalPointer()
            item_dest.copy_tree(item_src)
            self.treeChanged.emit()
            return True
        self.insert_item(
            parent, row, name, (criteria, columns), ItemType(int(item_type))
        )
        self.treeChanged.emit()
        return True

    def get_item(self, index: QModelIndex = QModelIndex()) -> TreeItem:
        """return ItemType from index"""
        if index.isValid():
            item: TreeItem = index.internalPointer()
            if item:
                return item

        return self.root_item

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        """return header data (override)"""
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.root_item.data(section)

        return None

    def index(
        self, row: int, column: int, parent: QModelIndex = QModelIndex()
    ) -> QModelIndex:
        """return index from row, column, parent (ovveride)"""
        if parent.isValid() and parent.column() != 0:
            return QModelIndex()

        parent_item: TreeItem = self.get_item(parent)
        if not parent_item:
            return QModelIndex()

        child_item: TreeItem = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()

    def insertColumns(
        self, position: int, columns: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        self.beginInsertColumns(parent, position, position + columns - 1)
        success: bool = self.root_item.insert_columns(position, columns)
        self.endInsertColumns()

        return success

    def insertRows(
        self, position: int, rows: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        parent_item: TreeItem = self.get_item(parent)
        if not parent_item:
            return False

        self.beginInsertRows(parent, position, position + rows - 1)
        column_count = self.root_item.column_count()
        success: bool = parent_item.insert_children(position, rows, column_count)
        self.endInsertRows()

        return success

    def parent(self, index: QModelIndex = QModelIndex()) -> QModelIndex:
        """return parent from index (override)"""
        if not index.isValid():
            return QModelIndex()

        child_item: TreeItem = self.get_item(index)
        if child_item:
            parent_item: TreeItem = child_item.parent()
        else:
            parent_item = None

        if parent_item == self.root_item or not parent_item:
            return QModelIndex()

        return self.createIndex(parent_item.child_number(), 0, parent_item)

    def removeColumns(
        self, position: int, columns: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        """remove columns from index (override)"""
        self.beginRemoveColumns(parent, position, position + columns - 1)
        success: bool = self.root_item.remove_columns(position, columns)
        self.endRemoveColumns()

        if self.root_item.column_count() == 0:
            self.removeRows(0, self.rowCount())

        return success

    def removeRows(
        self, position: int, rows: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        """remove rows from index (override)"""
        item: TreeItem = parent.internalPointer()
        log.info("removeRows(%s, %s, %s)", position, rows, item.item_data)
        parent_item: TreeItem = self.get_item(parent)
        if not parent_item:
            return False

        self.beginRemoveRows(parent, position, position + rows - 1)
        success: bool = parent_item.remove_children(position, rows)
        self.endRemoveRows()

        return success

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """return row count for index (override)"""
        if parent.isValid() and parent.column() > 0:
            return 0

        parent_item: TreeItem = self.get_item(parent)
        if not parent_item:
            return 0
        return parent_item.child_count()

    def setData(self, index: QModelIndex, value, role: int) -> bool:
        """set Data (override)"""

        item: TreeItem = self.get_item(index)

        if role == Qt.ItemDataRole.UserRole:
            name, criteria_columns, item_type = value
            item.item_data = [name]
            item.internal_data = criteria_columns
            item.item_type = item_type
            return True

        if role != Qt.ItemDataRole.EditRole:
            return False

        result: bool = item.set_data(index.column(), value)

        if result:
            self.dataChanged.emit(
                index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]
            )

        return result

    def setHeaderData(
        self, section: int, orientation: Qt.Orientation, value, role: int = None
    ) -> bool:
        """set header data (override)"""
        if role != Qt.ItemDataRole.EditRole or orientation != Qt.Orientation.Horizontal:
            return False

        result: bool = self.root_item.set_data(section, value)

        if result:
            self.headerDataChanged.emit(orientation, section, section)

        return result

    def _find_in_childs(self, item: TreeItem, part: str, case: bool = True) -> TreeItem:
        """(internal) find part foldername in items child, case sensitive by default"""
        for row in range(0, item.child_count()):
            child = item.child(row)
            if case:
                if child.item_data[0] == part:
                    return child
            else:
                if child.item_data[0].lower() == part.lower():
                    return child
        return None

    def pathToItem(self, path: str, case: bool = True) -> TreeItem | None:
        """return item from path, case sensitive by default"""
        item = self.root_item
        path = PurePosixPath(path)
        for part in path.parts:
            item = self._find_in_childs(item, part, case)
            if item is None:
                log.warning("pathToItem(%s) : part not found", path)
                return None
        return item

    def _getOrCreateChild(
        self, item_parent: TreeItem, name: str, data: any, item_type: ItemType
    ) -> TreeItem:
        """(internal) get or create child"""
        item = item_parent.find_child(name)
        if item is None:
            log.debug(
                "beginInsertRows parent:'%s', pos:%s",
                item_parent.item_data[0],
                item_parent.child_count(),
            )
            indexParent = self.createIndex(item_parent.row(), 0, item_parent)
            self.beginInsertRows(
                indexParent, item_parent.child_count(), item_parent.child_count()
            )
            item = TreeItem([name], data, item_type, item_parent)
            item_parent.add_child(item)
            self.endInsertRows()
        return item

    def append_child_item(
        self, index_parent: QModelIndex, name: str, userData: any, item_type: ItemType
    ) -> QModelIndex:
        """
        append child item (in last position) and return new index
        """
        row = self.rowCount(index_parent)
        if not self.insertRow(row, index_parent):
            return QModelIndex()
        index_new = self.index(row, 0, index_parent)
        self.setData(index_new, (name, userData, item_type), Qt.ItemDataRole.UserRole)
        return index_new

    def insert_item(
        self,
        index: QModelIndex,
        row: int,
        name: str,
        userData: any,
        item_type: ItemType,
    ) -> QModelIndex:
        """
        insert one item before index, return nex index
        """
        parent = index
        if not self.insertRow(row, parent):
            return QModelIndex()
        index_new = self.index(row, 0, parent)
        self.setData(index_new, (name, userData, item_type), Qt.ItemDataRole.UserRole)
        return index_new

    def createFromPath(
        self, path_name: str, data: any, item_type: ItemType
    ) -> QModelIndex:
        """
        create item and return index. Store Lightroom infos:
            - path_name : hierachical name,
            - data : any object depending item_type
            - item_type : object type (collection, keyword or folder)
        """
        item = self.root_item
        path = PurePosixPath(path_name)
        for part in path.parts:
            child = self._find_in_childs(item, part)
            if child is None:
                item = self._getOrCreateChild(item, part, data, item_type)
                log.debug("item created ")
            else:
                item = child
        return self.createIndex(item.row(), 0, item)

    def absolutePath(self, index: QModelIndex) -> str:
        """return absolute path for index"""
        if not index.isValid():
            return ""
        item = index.internalPointer()
        return item.absolutePath()

    def indexFromPath(self, path: str) -> QModelIndex:
        """return index from path"""
        path = PurePosixPath(path)
        item = self.pathToItem(path)
        if item is None:
            return QModelIndex()
        return self.createIndex(item.row(), 0, item)

    def itemType(self, index: QModelIndex) -> str:
        """return absolute path for index"""
        if not index.isValid():
            return ""
        item = index.internalPointer()
        return item.itemType()

    def userData(self, index: QModelIndex) -> str:
        """return absolute path for index"""
        if not index.isValid():
            return None
        item: TreeItem = index.internalPointer()
        return item.userData()

    def setUserData(self, index: QModelIndex, data) -> str:
        """return absolute path for index"""
        if not index.isValid():
            return None
        item: TreeItem = index.internalPointer()
        return item.set_userData(data)

    def _repr_recursion(self, item: TreeItem, indent: int = 0) -> str:
        """str() recursive function"""
        result = " " * indent + repr(item) + "\n"
        for child in item.child_items:
            result += self._repr_recursion(child, indent + 2)
        return result

    def __repr__(self) -> str:
        """str() function"""
        return self._repr_recursion(self.root_item)

    def toJson(self, index: QModelIndex) -> dict:
        """return tree as JSON"""
        if not index.isValid():
            index = self.indexFromPath("Query:")
        item: TreeItem = index.internalPointer()
        return self.__toJson(item)

    def __toJson(self, item: TreeItem) -> dict:
        tree = {
            "name": item.item_data[0],
            "type": item.item_type.value,
        }
        if item.item_type == ItemType.LRTOOLS_QUERY:
            criteria, columns = item.internal_data
            tree["criteria"] = criteria
            tree["columns"] = columns
        else:
            tree["data"] = item.internal_data

        tree["children"] = []
        for num in range(0, item.child_count()):
            child = item.child(num)
            tree["children"].append(self.__toJson(child))
        return tree

    def fromJson(self, path: str, queries: dict):
        """merge/replace queries"""

        item_type = ItemType(queries["type"])
        children = queries["children"]
        if item_type == ItemType.LRTOOLS_QUERY:
            data = (queries["criteria"], queries["columns"])
        else:
            data = queries["data"]

        if path:
            path = f"{path}/"
        path = f"{path}{queries['name']}"
        self.createFromPath(path, data, item_type)

        for child in children:
            self.fromJson(path, child)
