# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'query.ui'
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
    QApplication,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QWidget,
)


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName("Dialog")
        Dialog.resize(517, 218)
        self.gridLayout = QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.labelName = QLabel(Dialog)
        self.labelName.setObjectName("labelName")

        self.horizontalLayout.addWidget(self.labelName)

        self.queryName = QLineEdit(Dialog)
        self.queryName.setObjectName("queryName")

        self.horizontalLayout.addWidget(self.queryName)

        self.horizontalSpacer = QSpacerItem(
            80, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.labelQuery = QLabel(Dialog)
        self.labelQuery.setObjectName("labelQuery")

        self.horizontalLayout_2.addWidget(self.labelQuery)

        self.query = QLineEdit(Dialog)
        self.query.setObjectName("query")

        self.horizontalLayout_2.addWidget(self.query)

        self.btSelCriteria = QPushButton(Dialog)
        self.btSelCriteria.setObjectName("btSelCriteria")

        self.horizontalLayout_2.addWidget(self.btSelCriteria)

        self.gridLayout.addLayout(self.horizontalLayout_2, 1, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.label_3 = QLabel(Dialog)
        self.label_3.setObjectName("label_3")

        self.horizontalLayout_3.addWidget(self.label_3)

        self.columns = QLineEdit(Dialog)
        self.columns.setObjectName("columns")

        self.horizontalLayout_3.addWidget(self.columns)

        self.btSelColumns = QPushButton(Dialog)
        self.btSelColumns.setObjectName("btSelColumns")

        self.horizontalLayout_3.addWidget(self.btSelColumns)

        self.gridLayout.addLayout(self.horizontalLayout_3, 2, 0, 1, 1)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )

        self.gridLayout.addWidget(self.buttonBox, 3, 0, 1, 1)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)

    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", "Query Edit", None))
        self.labelName.setText(QCoreApplication.translate("Dialog", "Query Name", None))
        self.labelQuery.setText(QCoreApplication.translate("Dialog", "Query", None))
        self.btSelCriteria.setText(QCoreApplication.translate("Dialog", "Select", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", "Columns", None))
        self.btSelColumns.setText(QCoreApplication.translate("Dialog", "Select", None))

    # retranslateUi
