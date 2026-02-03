# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'columns.ui'
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
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QLineEdit,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName("Dialog")
        Dialog.resize(918, 666)
        self.gridLayout = QGridLayout(Dialog)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setSpacing(12)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_3.setSizeConstraint(
            QLayout.SizeConstraint.SetDefaultConstraint
        )
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(3)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_3 = QLabel(Dialog)
        self.label_3.setObjectName("label_3")

        self.verticalLayout.addWidget(self.label_3)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.filter_avail = QLineEdit(Dialog)
        self.filter_avail.setObjectName("filter_avail")

        self.horizontalLayout_6.addWidget(self.filter_avail)

        self.horizontalSpacer_2 = QSpacerItem(
            200, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
        )

        self.horizontalLayout_6.addItem(self.horizontalSpacer_2)

        self.verticalLayout.addLayout(self.horizontalLayout_6)

        self.columns_avail = QTableWidget(Dialog)
        if self.columns_avail.columnCount() < 2:
            self.columns_avail.setColumnCount(2)
        self.columns_avail.setObjectName("columns_avail")
        self.columns_avail.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.columns_avail.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.columns_avail.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.columns_avail.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.columns_avail.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.columns_avail.setColumnCount(2)
        self.columns_avail.horizontalHeader().setVisible(True)
        self.columns_avail.horizontalHeader().setStretchLastSection(True)
        self.columns_avail.verticalHeader().setVisible(False)

        self.verticalLayout.addWidget(self.columns_avail)

        self.horizontalLayout.addLayout(self.verticalLayout)

        self.verticalSpacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.horizontalLayout.addItem(self.verticalSpacer)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setSpacing(6)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label_4 = QLabel(Dialog)
        self.label_4.setObjectName("label_4")

        self.verticalLayout_2.addWidget(self.label_4)

        self.verticalSpacer_2 = QSpacerItem(
            20, 24, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum
        )

        self.verticalLayout_2.addItem(self.verticalSpacer_2)

        self.columns_selected = QTableWidget(Dialog)
        if self.columns_selected.columnCount() < 1:
            self.columns_selected.setColumnCount(1)
        self.columns_selected.setObjectName("columns_selected")
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.columns_selected.sizePolicy().hasHeightForWidth()
        )
        self.columns_selected.setSizePolicy(sizePolicy)
        self.columns_selected.setMaximumSize(QSize(200, 16777215))
        self.columns_selected.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.columns_selected.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.columns_selected.setColumnCount(1)
        self.columns_selected.horizontalHeader().setStretchLastSection(True)
        self.columns_selected.verticalHeader().setVisible(False)
        self.columns_selected.verticalHeader().setHighlightSections(False)

        self.verticalLayout_2.addWidget(self.columns_selected)

        self.horizontalLayout.addLayout(self.verticalLayout_2)

        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, -1, -1, 10)
        self.label_result = QLabel(Dialog)
        self.label_result.setObjectName("label_result")

        self.horizontalLayout_2.addWidget(self.label_result)

        self.columns_result = QLineEdit(Dialog)
        self.columns_result.setObjectName("columns_result")

        self.horizontalLayout_2.addWidget(self.columns_result)

        self.verticalLayout_3.addLayout(self.horizontalLayout_2)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )

        self.verticalLayout_3.addWidget(self.buttonBox)

        self.gridLayout.addLayout(self.verticalLayout_3, 0, 0, 1, 2)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)

    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(
            QCoreApplication.translate("Dialog", "Query Columns Selection", None)
        )
        self.label_3.setText(
            QCoreApplication.translate("Dialog", "Columns Available", None)
        )
        self.filter_avail.setPlaceholderText(
            QCoreApplication.translate("Dialog", "colums filter", None)
        )
        # if QT_CONFIG(accessibility)
        self.columns_avail.setAccessibleName("")
        # endif // QT_CONFIG(accessibility)
        self.label_4.setText(
            QCoreApplication.translate("Dialog", "Columns Selected", None)
        )
        # if QT_CONFIG(accessibility)
        self.columns_selected.setAccessibleName("")
        # endif // QT_CONFIG(accessibility)
        self.label_result.setText(
            QCoreApplication.translate("Dialog", "Query Columns", None)
        )
        # if QT_CONFIG(accessibility)
        self.columns_result.setAccessibleName("")


# endif // QT_CONFIG(accessibility)
# retranslateUi
