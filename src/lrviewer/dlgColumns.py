# pylint: disable=line-too-long,invalid-name
"""
Dialog query columns selection

For specifc column "count(<NAME>)" and "countby(<NAME>)" the dialog support
    only one occurence of these
Choice of the column counted is done on accept.
The better is to modify the query manually in URL or in dialog Create/Modify query
"""

import logging

from PySide6.QtWidgets import QDialog
from PySide6.QtWidgets import QTableWidgetItem, QAbstractItemView, QInputDialog
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtGui import QPalette

from ui.columns_ui import Ui_Dialog


log = logging.getLogger(__name__)

COLUMNS_DESC = {
    "name": 'base name (default), ex: "IMG_1101"',
    "name=basext": 'base name + extension, ex: "IMG_1101.jpg"',
    "name=full": 'path + base name + extension, ex: "D:/Photos/IMG_1101.jpg"',
    "name=base_vc": 'base name + virtual copy name, ex: "IMG_1101 Copy 1"',
    "name=basext_vc": 'base name + virtual copy name + extension, ex: "IMG_1101 - Copy 1.jpg"',
    "name=full_vc": 'path + base name + virtual copy name + extension, ex: "D:/Photos/IMG_1101 - Copy 1.jpg"',
    "folder": "Folder name",
    "id": "id photo (Adobe_images.id_local)",
    "uuid": "UUID photo (Adobe_images.id_global)",
    "rating": "Rating/note",
    "colorlabel": "Color and label",
    "datemod": "Last modificaton datetime",
    "datecapt": "Capture datetime",
    "modcount": "Number of modifications",
    "master": "Master image of virtual copy",
    # "xmp"        : "XMP metadatas.",
    "vname": "Virtual copy name",
    "stackpos": "Photo position in stack",
    "stack": "Stack identifier",
    "keywords": "Keywords list",
    "collections": "Collections list",
    "exif": '"var:SQLCOLUMN" : display column in table AgHarvestedExifMetadata. Ex: "exif=var:hasgps"',
    "extfile": "Extension of an external/extension file (jpg,xmp,...)",
    "dims": "Image dimensions in form <WIDTH>x<HEIGHT>",
    "aspectratio": "Aspect ratio (width/height)",
    "camera": "Camera name",
    "lens": "Lens name",
    "iso": "ISO value",
    "focal": "Focal lens",
    "aperture": "Aperture lens",
    "speed": "Speed shutter",
    "monochrome": "Monochrome image when = 1",
    "grayscale": "Monochrome image when = 1",
    "flash": "Flash use",
    "latitude": "GPS latitude",
    "longitude": "GPS longitude",
    "creator": "Photo creator",
    "caption": "Photo caption",
    "pubname": "Remote path and name of published photo",
    "pubcollection": "Name of publish collection",
    "pubtime": "Published datetime in seconds from 2001-1-1",
    "pubposition": "Order number in collection",
    "location": "Location name",
    "city": "Location city name",
    "country": "Location country name",
    "state": "Location state name",
    "duration": "Video duration in seconds",
    "count(<NAME>)": 'Count not NULL values in column <NAME>. Replace <NAME> by a valid column (ex: "count(master)")',
    "countby(<NAME>)": 'Count aggregated not NULL value for column <NAME>. Replace <NAME> by a valid column (ex: "countby(camera)")',
}


class ColumnsDialog(QDialog):
    """
    Dialog query columns selection
    """

    def __init__(self, columns="", parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # color indicator ok for label "query columns"
        self.colorLabel = self.ui.label_result.palette().color(QPalette.ColorRole.Text)

        # prepare available columns
        self.ui.columns_avail.setHorizontalHeaderLabels(["Column Name", "Description"])
        self.ui.columns_avail.setColumnWidth(0, 110)
        self.ui.columns_selected.setHorizontalHeaderLabels(["Column Name"])
        self.ui.columns_avail.itemDoubleClicked.connect(self.onAvailDoubleClicked)
        for num_row, (col_name, col_desc) in enumerate(COLUMNS_DESC.items()):
            self.ui.columns_avail.insertRow(num_row)
            self.ui.columns_avail.setItem(num_row, 0, QTableWidgetItem(col_name))
            self.ui.columns_avail.setItem(num_row, 1, QTableWidgetItem(col_desc))

        # prepare selected columns
        #
        # Note: we want reordering items in columns_selected by drag/drop. We need :
        #   setDragDropMode(InternalMove), setDragDropOverwriteMode(False)
        #   and for each item : item.setFlags(item->flags() & ~ ItemIsDropEnabled)
        # when drag is outside of items, current qt implementation fill item to None : we need to remove it
        self.ui.columns_selected.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.ui.columns_selected.setDragDropOverwriteMode(False)

        self.ui.columns_selected.itemDoubleClicked.connect(self.onSelectedDoubleClicked)
        self.ui.columns_selected.model().rowsMoved.connect(self.onSelectedRowsMoved)
        self.ui.columns_selected.model().rowsAboutToBeRemoved.connect(
            self.onSelectedRowsAboutToBeRemoved
        )
        self.ui.columns_selected.model().rowsRemoved.connect(self.onSelectedRowsRemoved)
        self.ui.columns_selected.cellChanged.connect(self.onSelectedCellChanged)

        self.ui.columns_result.textEdited.connect(self.onResultEdited)

        self.ui.filter_avail.textEdited.connect(self.onFilterEdited)

        # init columns selected
        self._init_columns_selected(columns.split(","))
        self.setColumnsResult()

    def _init_columns_selected(self, columns):
        """init columns selected"""
        for row, column in enumerate(columns):
            self.ui.columns_selected.insertRow(row)
            self.ui.columns_selected.setItem(row, 0, QTableWidgetItem(column))
            item = self.ui.columns_selected.item(row, 0)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)

            item_avail = self.findColumnAvail(column)
            if item_avail is None:
                log.error("column unsupported : %s", column)
                continue
            item_avail.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.ui.columns_avail.item(item.row(), 1).setFlags(
                item.flags() & ~Qt.ItemFlag.ItemIsEnabled
            )
        self.setColumnsResult()

    def onAvailDoubleClicked(self, item: QTableWidgetItem):
        """double click in avail : add column to selected"""
        row = self.ui.columns_selected.rowCount()
        self.ui.columns_selected.insertRow(row)

        item_avail = self.ui.columns_avail.item(item.row(), 0)
        item_avail.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        self.ui.columns_avail.item(item.row(), 1).setFlags(
            item.flags() & ~Qt.ItemFlag.ItemIsEnabled
        )

        text = item_avail.text()
        self.ui.columns_selected.setItem(row, 0, QTableWidgetItem(text))
        item = self.ui.columns_selected.item(row, 0)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)
        self.setColumnsResult()

    def onSelectedDoubleClicked(self, item: QTableWidgetItem):
        """double click in selected : remove column from selected"""
        self.ui.columns_selected.removeRow(item.row())
        # removeRow cause a call to onSelectedRowsAboutToBeRemoved
        self.setColumnsResult()

    def onSelectedCellChanged(self, row, column):
        """Cell changed

        In current Qt implementation, a drag outside of items clear the dragged cell :
            for keep coherence, this cell is removed
        """
        if self.ui.columns_selected.item(row, column) is None:
            self.ui.columns_selected.removeRow(row)

    def onSelectedRowsMoved(
        self, sourceParent, sourceStart, sourceEnd, destParent, destRow
    ):  # pylint: disable=unused-argument
        """columns_selected row moved : update query columns"""
        self.setColumnsResult()

    def onSelectedRowsAboutToBeRemoved(
        self, parent: QModelIndex, first, last
    ):  # pylint: disable=unused-argument
        """columns_selected about to be removed

        Unfortunaly the row to be deleted is already set to none (Qt bug ?): self.ui.columns_selected.item(first, 0) == None
        As fix around for get column name removed, we use columns_result at 'first' index
        """
        item = self.ui.columns_selected.item(first, 0)
        if item is None:
            column_del = self.ui.columns_result.text().split(",")[first]
        else:
            column_del = item.text()
        item_avail = self.findColumnAvail(column_del)
        item_avail.setFlags(item_avail.flags() | Qt.ItemFlag.ItemIsEnabled)
        self.ui.columns_avail.item(item_avail.row(), 1).setFlags(
            item_avail.flags() | Qt.ItemFlag.ItemIsEnabled
        )

    def onSelectedRowsRemoved(self, first, last):  # pylint: disable=unused-argument
        """columns_selected row removed : update query columns"""
        self.setColumnsResult()

    def onResultEdited(self, text):
        """columns result edited"""
        columns = [col.strip() for col in text.split(",")]
        valid = True
        for col in columns:
            if col not in COLUMNS_DESC:
                valid = False
                break
        if not valid:
            self.ui.label_result.setStyleSheet("color: red;")
            self.ui.buttonBox.setEnabled(False)
            return
        self.ui.label_result.setStyleSheet(f"color: {self.colorLabel.name()};")
        self.ui.buttonBox.setEnabled(True)
        # remove all selected and re-insert new
        self.ui.columns_selected.setRowCount(0)
        self._init_columns_selected(columns)

    def setColumnsResult(self):
        """set columns result from columns_selected"""
        columns = [
            self.ui.columns_selected.item(row, 0).text()
            for row in range(0, self.ui.columns_selected.rowCount())
        ]
        self.ui.columns_result.setText(",".join(columns))
        # sure here that results is OK
        self.ui.buttonBox.setEnabled(True)
        self.ui.label_result.setStyleSheet(f"color: {self.colorLabel.name()};")

    def findColumnAvail(self, text):
        """find column name in columns_avail and return item"""
        for row in range(0, self.ui.columns_avail.rowCount()):
            item = self.ui.columns_avail.item(row, 0)
            if item.text() == text:
                return item
        return None

    def onFilterEdited(self, text):
        """filter the available columns"""
        for row in range(0, self.ui.columns_avail.rowCount()):
            if not text:
                self.ui.columns_avail.setRowHidden(row, False)
                continue
            text0 = self.ui.columns_avail.item(row, 0).text()
            text1 = self.ui.columns_avail.item(row, 1).text()
            found = (text.lower() in text0.lower()) or (text.lower() in text1.lower())
            self.ui.columns_avail.setRowHidden(row, not found)

    def accept(self):
        """override accept : specific for count() and countby

        count and countby could be appear several times, but the dialog doesn't support that
        """

        def replace_count(func):
            retry = ""
            num_retry = 0
            while True:
                col_count, ok = QInputDialog.getText(
                    self,
                    f"Which column to use in '{func}()' ? {retry}",
                    "Column name : ",
                )
                if not ok:
                    return None
                else:
                    if col_count not in COLUMNS_DESC:
                        num_retry += 1
                        retry = f"Retry {num_retry}"
                        continue
                    # no more check, too tricky, but not all columns can be used in count
                    # insert in count/countby
                    return f"count({col_count})"

        columns = [col.strip() for col in self.ui.columns_result.text().split(",")]
        if "count(<NAME>)" in columns:
            new_column = replace_count("count")
            if new_column is None:
                # no column choosen in count : do not valid the dialog :
                return
            index = columns.index("count(<NAME>)")
            columns[index] = new_column
            self.ui.columns_result.setText(",".join(columns))
        if "countby(<NAME>)" in columns:
            new_column = replace_count("countby")
            if new_column is None:
                # no column choosen in count : do not valid the dialog :
                return
            index = columns.index("countby(<NAME>)")
            columns[index] = new_column
            self.ui.columns_result.setText(",".join(columns))

        # accept / close dialog
        super().accept()
