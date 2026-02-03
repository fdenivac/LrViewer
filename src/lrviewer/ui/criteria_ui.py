# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'criteria.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (
    QCoreApplication,
    QDate,
    QDateTime,
    QLocale,
    QMetaObject,
    QObject,
    QPoint,
    QRect,
    QSize,
    QTime,
    QUrl,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QCursor,
    QFont,
    QFontDatabase,
    QGradient,
    QIcon,
    QImage,
    QKeySequence,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
    QRadialGradient,
    QTransform,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName("Dialog")
        Dialog.setEnabled(True)
        Dialog.resize(937, 468)
        self.verticalLayoutWidget_4 = QWidget(Dialog)
        self.verticalLayoutWidget_4.setObjectName("verticalLayoutWidget_4")
        self.verticalLayoutWidget_4.setGeometry(QRect(10, 10, 141, 351))
        self.verticalLayoutWidget_4.setAutoFillBackground(False)
        self.verticalLayout_4 = QVBoxLayout(self.verticalLayoutWidget_4)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.label_2 = QLabel(self.verticalLayoutWidget_4)
        self.label_2.setObjectName("label_2")
        self.label_2.setAutoFillBackground(False)
        self.label_2.setFrameShape(QFrame.Shape.Panel)
        self.label_2.setFrameShadow(QFrame.Shadow.Sunken)
        self.label_2.setLineWidth(2)
        self.label_2.setMidLineWidth(1)

        self.verticalLayout_4.addWidget(self.label_2)

        self.criteria_filter = QLineEdit(self.verticalLayoutWidget_4)
        self.criteria_filter.setObjectName("criteria_filter")

        self.verticalLayout_4.addWidget(self.criteria_filter)

        self.criteria_list = QListWidget(self.verticalLayoutWidget_4)
        self.criteria_list.setObjectName("criteria_list")

        self.verticalLayout_4.addWidget(self.criteria_list)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.setGeometry(QRect(650, 440, 279, 24))
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.verticalLayoutWidget = QWidget(Dialog)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(170, 60, 301, 241))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label_4 = QLabel(self.verticalLayoutWidget)
        self.label_4.setObjectName("label_4")
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_4.sizePolicy().hasHeightForWidth())
        self.label_4.setSizePolicy(sizePolicy)

        self.verticalLayout.addWidget(self.label_4)

        self.text_description = QTextEdit(self.verticalLayoutWidget)
        self.text_description.setObjectName("text_description")
        self.text_description.setEnabled(False)
        self.text_description.setLineWidth(2)
        self.text_description.setReadOnly(True)

        self.verticalLayout.addWidget(self.text_description)

        self.horizontalLayoutWidget = QWidget(Dialog)
        self.horizontalLayoutWidget.setObjectName("horizontalLayoutWidget")
        self.horizontalLayoutWidget.setGeometry(QRect(10, 390, 911, 41))
        self.horizontalLayout = QHBoxLayout(self.horizontalLayoutWidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.label_6 = QLabel(self.horizontalLayoutWidget)
        self.label_6.setObjectName("label_6")

        self.horizontalLayout.addWidget(self.label_6)

        self.criteria_result = QLineEdit(self.horizontalLayoutWidget)
        self.criteria_result.setObjectName("criteria_result")
        self.criteria_result.setEnabled(True)
        self.criteria_result.setReadOnly(True)

        self.horizontalLayout.addWidget(self.criteria_result)

        self.verticalLayoutWidget_5 = QWidget(Dialog)
        self.verticalLayoutWidget_5.setObjectName("verticalLayoutWidget_5")
        self.verticalLayoutWidget_5.setGeometry(QRect(490, 10, 431, 341))
        self.verticalLayoutWidget_5.setAutoFillBackground(False)
        self.verticalLayout_5 = QVBoxLayout(self.verticalLayoutWidget_5)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.verticalLayoutWidget_5)
        self.label_3.setObjectName("label_3")
        self.label_3.setAutoFillBackground(False)
        self.label_3.setFrameShape(QFrame.Shape.Panel)
        self.label_3.setFrameShadow(QFrame.Shadow.Sunken)
        self.label_3.setLineWidth(2)
        self.label_3.setMidLineWidth(1)

        self.verticalLayout_5.addWidget(self.label_3)

        self.criteria_selected = QTableWidget(self.verticalLayoutWidget_5)
        if self.criteria_selected.columnCount() < 3:
            self.criteria_selected.setColumnCount(3)
        self.criteria_selected.setObjectName("criteria_selected")
        self.criteria_selected.setDragDropOverwriteMode(False)
        self.criteria_selected.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.criteria_selected.setColumnCount(3)
        self.criteria_selected.horizontalHeader().setVisible(True)
        self.criteria_selected.verticalHeader().setVisible(False)

        self.verticalLayout_5.addWidget(self.criteria_selected)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)

    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", "Dialog", None))
        self.label_2.setText(
            QCoreApplication.translate("Dialog", "Criteria Name", None)
        )
        self.criteria_filter.setPlaceholderText(
            QCoreApplication.translate("Dialog", "Filter", None)
        )
        self.label_4.setText(
            QCoreApplication.translate("Dialog", "Criteria Description", None)
        )
        self.label_6.setText(
            QCoreApplication.translate("Dialog", "Criteria List : ", None)
        )
        self.label_3.setText(
            QCoreApplication.translate("Dialog", "Criteria Selected", None)
        )

    # retranslateUi
