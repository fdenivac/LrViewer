# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'catalogs_managerxzFsL.ui'
##
## Created by: Qt User Interface Compiler version 6.11.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(841, 246)
        self.formLayout = QFormLayout(Dialog)
        self.formLayout.setObjectName(u"formLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.list_catalogs = QListWidget(Dialog)
        self.list_catalogs.setObjectName(u"list_catalogs")

        self.horizontalLayout.addWidget(self.list_catalogs)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.bt_configure = QPushButton(Dialog)
        self.bt_configure.setObjectName(u"bt_configure")

        self.verticalLayout_4.addWidget(self.bt_configure)

        self.bt_delete = QPushButton(Dialog)
        self.bt_delete.setObjectName(u"bt_delete")

        self.verticalLayout_4.addWidget(self.bt_delete)


        self.horizontalLayout.addLayout(self.verticalLayout_4)


        self.formLayout.setLayout(0, QFormLayout.ItemRole.FieldRole, self.horizontalLayout)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Ok)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.buttonBox)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Catalogs Management", None))
        self.bt_configure.setText(QCoreApplication.translate("Dialog", u"Configure", None))
        self.bt_delete.setText(QCoreApplication.translate("Dialog", u"Delete", None))
    # retranslateUi

