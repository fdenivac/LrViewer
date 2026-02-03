# pylint: disable=line-too-long,invalid-name
"""
Dialogs based on UI files
"""

from PySide6.QtWidgets import (
    QDialog,
)
from PySide6.QtGui import QTextDocument

from settings import APP_NAME, APP_VERSION
from dlgColumns import ColumnsDialog
from dlgCriteria import CriteriaDialog

from ui.about_ui import Ui_Dialog as UiAboutDialog
from ui.query_ui import Ui_Dialog as UiQueryDialog


class AboutDialog(QDialog):
    """about application dialog"""

    def __init__(self, parent=None):
        def replace(placeholder, newString):
            cursor = doc.find(placeholder, 0, QTextDocument.FindFlag.FindWholeWords)
            if not cursor.isNull():
                cursor.insertText(newString)

        super().__init__(parent)

        self.ui = UiAboutDialog()
        self.ui.setupUi(self)
        doc = self.ui.textEdit.document()
        replace("<APPNAME>", APP_NAME)
        replace("<VERSION>", APP_VERSION)


class QueryDialog(QDialog):
    """new or edit query dialog"""

    def __init__(self, name, query="", columns="", parent=None):
        super().__init__(parent)
        self.ui = UiQueryDialog()
        self.ui.setupUi(self)

        self.ui.btSelColumns.clicked.connect(self.onSelColumns)
        self.ui.btSelCriteria.clicked.connect(self.onSelCriteria)
        self.ui.queryName.setText(name)
        self.ui.queryName.selectAll()
        self.ui.queryName.setFocus()
        self.ui.query.setText(query)
        self.ui.columns.setText(columns)

    def onSelColumns(self):
        """open dialog sel columns"""
        dialog = ColumnsDialog(self.ui.columns.text(), self)
        if not dialog.exec():
            return
        self.ui.columns.setText(dialog.ui.columns_result.text())

    def onSelCriteria(self):
        """open dialog selection criteria"""
        dialog = CriteriaDialog(self.ui.query.text(), self)
        if not dialog.exec():
            return
        self.ui.query.setText(dialog.ui.criteria_result.text())
