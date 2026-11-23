"""
Dialog for plugin dir_prod

"""

import logging

from PySide6.QtWidgets import (
    QDialog,
)
from PySide6.QtWidgets import (
    QFileDialog,
)

from plugins.thumbsource.dirprod_ui import Ui_Dialog


class ConfigDialog(QDialog):
    """
    Dialog plugin configuration
    """

    DATE_FORMATS = {
        "Year": "%Y",
        "Year/Month": "%Y/%m",
        "Year/Month/Day": "%Y/%m/%d",
    }
    DATE_FORMATS_REVERSE = {v: k for k, v in DATE_FORMATS.items()}

    def __init__(self, prod_dir, fmt_date, parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self._load_formats_combo()

        self.ui.date_format.textChanged.connect(self.onDateFormatChanged)

        self.ui.prod_dir.setText(prod_dir)
        self.ui.date_format.setText(fmt_date)

        self.ui.btSelDir.clicked.connect(self.onSelDirectory)
        self.ui.comboFormat.currentIndexChanged.connect(self.onFormatChanged)

    def _load_formats_combo(self):
        """load date formats combo box"""
        for fmt, raw in self.DATE_FORMATS.items():
            self.ui.comboFormat.addItem(fmt, raw)

    def onDateFormatChanged(self):
        """change date format"""
        fmt_date = self.ui.date_format.text()
        if fmt_date in self.DATE_FORMATS_REVERSE:
            self.ui.comboFormat.setCurrentText(self.DATE_FORMATS_REVERSE[fmt_date])
        else:
            self.ui.comboFormat.setCurrentText("")

    def onSelDirectory(self):
        """click button choose prodcution directory"""

        prod_dir = QFileDialog.getExistingDirectory(
            self,
            "Choose Production Directory",
            self.ui.prod_dir.text(),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )
        self.ui.prod_dir.setText(prod_dir)

    def onFormatChanged(self, index):
        """change format of date capture"""
        fmt_date = self.ui.comboFormat.currentData()
        self.ui.date_format.setText(fmt_date)

    def accept(self):
        super().accept()
