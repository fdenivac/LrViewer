# pylint: disable=line-too-long,invalid-name
"""
Dialog for  criteria selection

"""

import logging

from PySide6.QtWidgets import (
    QDialog,
)
from PySide6.QtWidgets import (
    QListWidgetItem,
    QLineEdit,
    QTableWidgetItem,
    QComboBox,
    QStyledItemDelegate,
    QAbstractItemView,
    QHeaderView,
    QMessageBox,
)

# from PySide6.uic import loadUi
from PySide6.QtGui import (
    # QRegularExpression,
    QRegularExpressionValidator,
    # QValidator,
)
from PySide6.QtCore import (
    Qt,
    QRegularExpression,
    Signal,
    QEvent,
)

from ui.criteria_ui import Ui_Dialog


log = logging.getLogger(__name__)

PH_STR_OR_WILDCARDS = "string and wildchards '%'"
PH_STR_OR_NULL = "string and wildchards '%', 'null'"
PH_INTEGER = "an integer"
PH_FLOAT = "a float"
REGEX_INT = r"[0-9]\d{1,8}"
REGEX_FLOAT = r"(?:\d+(?:\.\d*)?|\.\d+)"

CRITERIA_DESC = {
    "name": {
        "help": "Photo Name : the base name + copyname only (wildcards %)",
        "type": "str",
        "placeholder": PH_STR_OR_WILDCARDS,
    },
    "ext": {
        "help": "Photo Extension Name : as .jpg,.nef,... (can use wildcards %)",
        "type": "str",
        "placeholder": PH_STR_OR_WILDCARDS,
    },
    "extfile": {
        "help": "File associated to photo (can use wildcards %)",
        "type": "str",
        "placeholder": PH_STR_OR_WILDCARDS,
    },
    "folder": {
        "help": "Folder name (or part of path) with optional wildcard '%' (ex: folder=%family%)",
        "type": "str",
        "placeholder": PH_STR_OR_WILDCARDS,
    },
    "idfolder": {
        "help": "Folder id (id_local of table AgLibraryFolder)",
        "type": "int",
        "placeholder": PH_INTEGER,
    },
    "datecapt": {
        "help": "Date and Time of Capture. Can be a complete year (2001) or month (2003/05) ",
        "op": ["=", "!=", ">", ">=", "<", "<="],
        "type": "date",
        "placeholder": "as '2012', '2015/5', '2020/10/25'",
    },
    "videos": {
        "help": "Videos or Photos selection."
        "When this criteria is not specified, photos AND videos are selected."
        "'videos=true' can be written 'videos'",
        "type": "choices",
        "values": ["true", "false"],
    },
    "vcopies": {
        "help": "Virtual Copies selection",
        "type": "choices_or_value",
        "placeholder": "bool or value",
        "values": ["true", "false", "<MASTER_IMAGE>"],
    },
    "flag": {
        "help": "Flag status : photos flagged, unflagged, rejected",
        "type": "choices",
        "values": ["flagged", "unflagged", "rejected"],
    },
    "rating": {
        "help": "Photo rating (note, stars) from 0 to 5",
        "op": ["=", "!=", ">", ">=", "<", "<="],
        "type": "choices",
        "values": ["0", "1", "2", "3", "4", "5"],
    },
    "colorlabel": {
        "help": "color or label.\n"
        "can be a string with wildcards, 'null' for photos without colorlabel\n",
        "type": "str",
        "placeholder": PH_STR_OR_NULL,
    },
    "creator": {
        "help": "Photo creator, with optional wildcards '%'",
        "type": "str",
        "placeholder": PH_STR_OR_WILDCARDS,
    },
    "copyright": {
        "help": "Photo copyright, with optional wildcards '%'",
        "type": "str",
        "placeholder": PH_STR_OR_NULL,
    },
    "title": {
        "help": "Photo title, with optional wildcards '%'",
        "type": "str",
        "placeholder": "",
    },
    "caption": {
        "help": "Photo caption, with optional wildcards '%'",
        "type": "str",
        "placeholder": PH_STR_OR_NULL,
    },
    "aperture": {
        "help": "Camera aperture. ex: 'f5.6', '2.8', '22'",
        "op": [">", ">=", "<", "<=", "=", "!="],
        "type": "aperture",
        "placeholder": "as: f5.6', '2.8', '22'...",
        "regex": r"[f]*-?\d+(?:\.\d+)?",
    },
    "speed": {
        "help": "Cameara Shutter Speed.",
        "type": "str",
        "op": [">", ">=", "<", "<=", "=", "!="],
        "placeholder": "as: 1/128, 2,...",
        "regex": r"(?:1\/)*\d+",
    },
    "iso": {
        "help": "Camera Shutter Speed.",
        "type": "int",
        "op": [">", ">=", "<", "<=", "=", "!="],
        "placeholder": PH_INTEGER,
        "regex": REGEX_INT,
    },
    "focal": {
        "help": "Lens Focal",
        "type": "float",
        "op": [">", ">=", "<", "<=", "=", "!="],
        "placeholder": PH_FLOAT,
        "regex": REGEX_FLOAT,
    },
    "flash": {
        "help": "Flash used",
        "type": "choices",
        "values": ["true", "false"],
    },
    "camera": {
        "help": "Camera Name",
        "type": "str",
        "placeholder": PH_STR_OR_WILDCARDS,
    },
    "camerasn": {
        "help": "Camera Serial NumberName",
        "type": "str",
        "placeholder": PH_STR_OR_WILDCARDS,
    },
    "lens": {
        "help": "Lens Name",
        "type": "str",
        "placeholder": PH_STR_OR_WILDCARDS,
    },
    "aspectratio": {
        "help": "Photo Aspect Ratio",
        "op": ["=", ">", ">=", "<", "<=", "!="],
        "type": "float",
        "placeholder": "a float as '1.5'",
        "regex": REGEX_FLOAT,
    },
    "width": {
        "help": "Photo width. Warning: the column 'dims' must be present",
        "op": ["=", ">", ">=", "<", "<=", "!="],
        "type": "int",
        "placeholder": PH_INTEGER,
        "regex": REGEX_INT,
    },
    "height": {
        "help": "Photo height. Warning: the column 'dims' must be present",
        "op": ["=", ">", ">=", "<", "<=", "!="],
        "type": "int",
        "placeholder": PH_INTEGER,
        "regex": REGEX_INT,
    },
    "monochrome": {
        "help": "Select photo natively in monochrome (black & white).",
        "type": "choices",
        "values": ["true", "false"],
    },
    "grayscale": {
        "help": "Select photos with grayscale (black & white) treatment by Lightroom development module.",
        "type": "choices",
        "values": ["true", "false"],
    },
    "hasgps": {
        "help": "Photos with geolocalisation GPS infos (latitude, longitude)",
        "type": "choices",
        "values": ["true", "false"],
    },
    "gps": {
        "help": "Select geolocalized photos around specification (square or rectangle)\n"
        "Can be :\n"
        " * 1 GPS coordinates (center) + square dimension in km, as '45.78;-2.54+100'\n"
        " * 2 GPS coordinates, as '45.78;-2.51/46.01;1.05'\n"
        " * 1 address + square dimension in km, as 'paris+50'\n"
        " * 2 addresses, as 'paris/geneve'\n"
        " * 'photo': + base name of geolocalized photo + square dimension in km,  as 'photo:DSC_1105+2'",
        "type": "str",
        "placeholder": "GPS coordinates, town, dimensions,...",
    },
    "country": {
        "help": "Select country with optional jokers '%'.\n"
        "'country=null' select photos without country\n",
        "type": "str",
        "placeholder": PH_STR_OR_NULL,
    },
    "state": {
        "help": "Select state with optional jokers '%'.\n"
        "'state=null' select photos without state\n",
        "type": "str",
        "placeholder": PH_STR_OR_NULL,
    },
    "city": {
        "help": "Select city with optional jokers '%'.\n"
        "'city=null' select photos without city\n",
        "type": "str",
        "placeholder": PH_STR_OR_NULL,
    },
    "location": {
        "help": "Select location with optional jokers '%'.\n"
        "'location=null' select photos without location\n",
        "type": "str",
        "placeholder": PH_STR_OR_NULL,
    },
    "haskeywords": {
        "help": "Select photos with or without any keywords ",
        "type": "choices",
        "values": ["true", "false"],
    },
    "keyword": {
        "help": "Photos with Keyword name (use wildcards '%')",
        "type": "str",
        "placeholder": PH_STR_OR_WILDCARDS,
    },
    "idkeyword": {
        "help": "Keyword id (id_local of table AgLibraryKeyword)",
        "type": "int",
        "placeholder": PH_INTEGER,
    },
    "collection": {
        "help": "Photos Collection name",
        "type": "str",
        "placeholder": PH_STR_OR_WILDCARDS,
    },
    "idcollection": {
        "help": "Collection id (id_local of tabe AgLibraryCollection) name",
        "type": "int",
        "placeholder": PH_INTEGER,
    },
    "pubcollection": {
        "help": "Photos Published Collection name\n"
        " * collection(s) name with wildcards '%'\n"
        " * 'true' for all photos published in all collections",
        "type": "str",
        "placeholder": "string with widcards or 'true' for all photos",
    },
    "idpubcollection": {
        "help": "id Published Collection (id_local of table AgLibraryPublishedCollection)",
        "type": "int",
        "placeholder": PH_INTEGER,
    },
    "pubtime": {
        "help": "Publication Datetime",
        "op": [">", ">=", "<", "<="],
        "type": "date",
        "placeholder": "as '2012', '2015/5', '2020/10/25'",
    },
    "metastatus": {
        "help": "Select photos according to metadatas status :\n"
        " * 'conflict' = metadatas different on disk from db\n"
        " * 'changedondisk' = metadata changed externally on disk\n"
        " * 'hasbeenchanged' = to be save on disk\n"
        " * 'conflict' = metadatas different on disk from db\n"
        " * 'uptodate' = uptodate, in error, or to write on disk\n"
        " * 'unknown' = write error, phot missing ...\n",
        "type": "choices",
        "values": [
            "hasbeenchanged",
            "conflict",
            "changedondisk",
            "unknown",
            "uptodate",
        ],
    },
    "stacks": {
        "help": "Select photos stacked:\n"
        " * top : photos at the top of each stack\n"
        " * no : photos not in stack\n"
        " * all : photos in stack (at top or not)\n"
        " * no+top : photos at top of stack + photos not in stack\n"
        "\n"
        "can be also a specific photo identified by id_local\n",
        "type": "choices",
        "values": ["top", "no", "no+top", "all"],
    },
    # TODO "exifindex"
    "sort": {
        "help": "(pseudo criter) allow to sort photos results.\n"
        "Can be a column number (one based) or column name",
        "type": "str",
        "placeholder": "column number, or column name",
    },
    "distinct": {
        "help": "(pseudo criter) remove duplicate lines from results",
        "type": "none",
    },
    "count": {
        "help": "(pseudo criter) criteria value for a column counted as 'countby(name)'. \n"
        "The value is in form : '<column name counted>=<operation><value>'\n"
        " Example for select duplicate files names: \n"
        "       columns are 'name,countby(name)'\n"
        "       criteria is 'count=name>1'.\n",
        "type": "str",
    },
}


class CriteriasEdit(QLineEdit):
    """QLineEdit with doubleclick detection"""

    doubleClicked = Signal()

    def event(self, event):
        if event.type() == QEvent.Type.MouseButtonDblClick:
            self.doubleClicked.emit()
            return True
        return super().event(event)


class CustomDelegate(QStyledItemDelegate):
    """delegate for create editor by type"""

    def createEditor(self, parent, option, index):
        """editor following criteria description"""
        if index.column() == 0:
            return super().createEditor(parent, option, index)
        # get criter in fisrt column
        index0 = index.model().createIndex(index.row(), 0, index.parent())
        criteria = index0.data(Qt.ItemDataRole.DisplayRole)
        desc = CRITERIA_DESC[criteria]
        desc_op = desc["op"] if "op" in desc else ["="]
        desc_type = desc["type"]

        if index.column() == 1:
            # column operator
            combo = QComboBox(parent)
            combo.addItems(desc_op)
            return combo

        if index.column() == 2:
            # column value
            if desc_type in ["choices", "choices_or_value"]:
                combo = QComboBox(parent)
                combo.addItems(desc["values"])
                if desc_type == "choices_or_value":
                    combo.setEditable(True)
                return combo
            if desc_type in ["str", "int", "aperture", "float", "speed"]:
                edit = QLineEdit(parent)
                if "placeholder" in desc:
                    edit.setPlaceholderText(desc["placeholder"])
                if "regex" in desc:
                    validator = QRegularExpressionValidator(
                        QRegularExpression(desc["regex"])
                    )
                    edit.setValidator(validator)
                return edit

        return super().createEditor(parent, option, index)


class CriteriaDialog(QDialog):
    """
    Dialog Criterias selection

    """

    def __init__(self, criteria="", parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.criteria_selected.setHorizontalHeaderLabels(["Name", "Op", "Value"])
        self.ui.criteria_selected.setColumnWidth(0, 100)
        self.ui.criteria_selected.setColumnWidth(1, 50)
        self.ui.criteria_selected.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.ui.criteria_selected.setEditTriggers(
            QAbstractItemView.EditTrigger.AllEditTriggers
        )
        delegate = CustomDelegate()
        self.ui.criteria_selected.setItemDelegateForColumn(1, delegate)
        self.ui.criteria_selected.setItemDelegateForColumn(2, delegate)
        self.ui.criteria_selected.itemChanged.connect(
            self.onCriteriaSelectedItemChanged
        )
        self.ui.criteria_selected.doubleClicked.connect(
            self.onCriteriaSelectedDoubleClicked
        )
        self._init_criteria_selected(criteria.split(","))

        self.ui.criteria_filter.textEdited.connect(self.onCriteriaFilter)

        # replace self.ui.criteria_result QLineEdit by CriteriasEdit
        self.ui.criteria_result.close()
        del self.ui.criteria_result
        self.ui.criteria_result = CriteriasEdit(parent=self.ui.horizontalLayoutWidget)
        self.ui.criteria_result.setObjectName("criteria_result")
        self.ui.criteria_result.setReadOnly(True)
        self.ui.horizontalLayout.addWidget(self.ui.criteria_result)

        for crit_name in CRITERIA_DESC:
            self.ui.criteria_list.addItem(QListWidgetItem(crit_name))
        self.ui.criteria_list.doubleClicked.connect(self.onCriteriaListDoubleClicked)
        self.ui.criteria_list.currentRowChanged.connect(self.onCriteriaListRowChanged)
        self.ui.criteria_result.doubleClicked.connect(self.onResultsDoubleClicked)
        # recompute criteria_result
        self.onCriteriaSelectedItemChanged()

    def _init_criteria_selected(self, criteria):
        """init columns selected"""
        for keyval in criteria:
            self._set_criteria_selected(keyval)

    def _set_criteria_selected(self, keyval):
        """set new criteria"""
        pos = keyval.find("=")
        if pos == -1:
            key = keyval
            oper = "="
            val = ""
        else:
            key = keyval[0:pos]
            p = 0
            for p, c in enumerate(keyval[pos + 1 :]):
                if c == "%":
                    break
                if not c.isalnum():
                    continue
                break
            if p == 0:
                oper = "="
                val = keyval[pos + 1 :]
            else:
                oper = keyval[pos + 1 : pos + 1 + p]
                val = keyval[pos + 1 + p :]

        if not key in CRITERIA_DESC:
            log.error("no '%s' criter", key)
            QMessageBox.critical(self, "Error", f"Criter unsupported: {key}")
            return

        row = self.ui.criteria_selected.rowCount()
        self.ui.criteria_selected.insertRow(row)
        self.ui.criteria_selected.setItem(row, 0, QTableWidgetItem(key))
        item = self.ui.criteria_selected.item(row, 0)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.ui.criteria_selected.setItem(row, 1, QTableWidgetItem(oper))
        self.ui.criteria_selected.setItem(row, 2, QTableWidgetItem(val))

    def onCriteriaListRowChanged(self, _):
        """Row Changed : show descrition"""
        crit = self.ui.criteria_list.currentItem().text()
        crit_desc = CRITERIA_DESC[crit]
        # fmt:off   ->avoid black crash
        text = f"{crit} : \n\n{crit_desc["help"]}"
        # fmt:off
        self.ui.text_description.setText(text)

    def onCriteriaListDoubleClicked(self):
        """doubleclick on criteria list : add criteria"""
        criteria_name = self.ui.criteria_list.currentItem().text()
        criteria_desc = CRITERIA_DESC[criteria_name]
        row = self.ui.criteria_selected.rowCount()
        self.ui.criteria_selected.insertRow(row)
        # criteria name not editable
        self.ui.criteria_selected.setItem(row, 0, QTableWidgetItem(criteria_name))
        item = self.ui.criteria_selected.item(row, 0)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if criteria_desc["type"] == "none":
            return
        # operator
        self.ui.criteria_selected.setItem(
            row,
            1,
            QTableWidgetItem(criteria_desc["op"][0] if "op" in criteria_desc else "="),
        )
        # choices : first value by default
        if criteria_desc["type"] in ["choices", "choices_or_value"]:
            self.ui.criteria_selected.setItem(
                row, 2, QTableWidgetItem(criteria_desc["values"][0])
            )

    def onCriteriaFilter(self, text):
        """text changed in criteria filter"""
        for row in range(0, self.ui.criteria_list.count()):
            item = self.ui.criteria_list.item(row)
            if not text:
                item.setHidden(False)
                continue
            # find in criter name and help
            crit = item.text()
            desc = CRITERIA_DESC[crit]
            if "help" in desc:
                found = (text.lower() in crit.lower()) or (
                    text.lower() in desc["help"].lower()
                )
            else:
                found = text.lower() in crit.lower()
            item.setHidden(not found)

    def onCriteriaSelectedItemChanged(self, _=None):
        """item changed in criteria_selected"""
        criteria = []
        for row in range(0, self.ui.criteria_selected.rowCount()):
            crit = self.ui.criteria_selected.item(row, 0).text()
            if not crit in CRITERIA_DESC:
                log.error("no '%s' criter", crit)
                continue
            criter = CRITERIA_DESC[crit]
            item = self.ui.criteria_selected.item(row, 1)
            op = item.text() if item else ""
            item = self.ui.criteria_selected.item(row, 2)
            val = item.text() if item else ""  # TODO invalid ?
            if criter["type"] in ["choices", "choices_or_value"] and (
                not val or val == "true"
            ):
                criteria.append(f"{crit}")
            elif criter["type"] == "none":
                criteria.append(f"{crit}")
            else:
                if op == "=":
                    op = ""
                criteria.append(f"{crit}={op}{val}")
        self.ui.criteria_result.setText(",".join(criteria))

    def onCriteriaSelectedDoubleClicked(self, index):
        """doubleclick on criteria_selected : remove criter"""
        row = index.row()
        self.ui.criteria_selected.removeRow(row)
        self.onCriteriaSelectedItemChanged()

    def onResultsDoubleClicked(self):
        """cursor position changed"""
        criteria = self.ui.criteria_result.text()
        pos = self.ui.criteria_result.cursorPosition()
        pos_prev = criteria.rfind(",", 0, pos)
        pos_next = criteria.find(",", pos)
        if pos_prev == -1:
            pos_prev = 0
        else:
            pos_prev += 1
        if pos_next == -1:
            pos_next = len(criteria)
        self.ui.criteria_result.setSelection(pos_prev, pos_next - pos_prev)
