# -*- encoding: utf-8 -*-
# pylint: disable=too-many-lines,disable=line-too-long,invalid-name,attribute-defined-outside-init


"""

Combobox URL History

"""
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox

from settings import settings

# logger
log = logging.getLogger(__name__)


class ComboHistory(QComboBox):
    """combobox with history functions"""

    def __init__(self, fixCase=False, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setMinimumWidth(500)
        self.setMaxVisibleItems(20)
        self.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)
        self.max_history_entries = settings.value("MaxHistoryEntries", 100)
        if fixCase:
            self.editTextChanged.connect(self.onEditTextChanged)

    def setText(self, text):
        """set text"""
        log.info("urlCombo setText %s", text)
        cur_index = self.currentIndex()
        cur_text = self.itemText(cur_index)
        if cur_text == text:
            return
        # urls from 0 to cur_index are reversed
        moves = [self.itemText(index) for index in range(0, cur_index + 1)]
        for pos, move in enumerate(reversed(moves)):
            self.setItemText(pos, move)
        # new text is inserted at pos 0
        if self.count() == self.max_history_entries:
            self.removeItem(self.count() - 1)
        self.insertItem(0, text, None)
        self.setCurrentIndex(0)

    def text(self) -> str:
        """return text"""
        return self.currentText()

    def back(self) -> str:
        """previous index"""
        index = self.currentIndex()
        if index == -1:
            return ""
        index += 1
        if index >= self.count():
            return ""
        self.setCurrentIndex(index)
        return self.text()

    def forward(self) -> str:
        """next index"""
        index = self.currentIndex()
        if index in [-1, 0]:
            return ""
        index -= 1
        self.setCurrentIndex(index)
        return self.text()

    def isFirst(self) -> bool:
        """True is current index is first element (=> no forward)"""
        return self.currentIndex() <= 0

    def isLast(self) -> bool:
        """True is current index is last element or not set (no back)"""
        return self.currentIndex() + 1 == self.count() or self.currentIndex() == -1

    def onEditTextChanged(self, text):
        """edit text changed : force to current

        fix around with case (lowercase/uppercase) problem :
            when a text is in combo, impossible to modify the case
        note: the setDuplicatesEnable doesn't help

        """
        index = self.findText(text, Qt.MatchFlag.MatchFixedString)
        if index < 0:
            return
        if self.itemText(index) != text:
            pos = self.lineEdit().cursorPosition()
            self.setItemText(index, text)
            self.lineEdit().setCursorPosition(pos)
