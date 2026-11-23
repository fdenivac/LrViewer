# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'catalog_settingsjaPdQT.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QCheckBox, QComboBox,
    QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(531, 250)
        self.gridLayout = QGridLayout(Dialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.checkbox_allow_thumbs = QCheckBox(Dialog)
        self.checkbox_allow_thumbs.setObjectName(u"checkbox_allow_thumbs")

        self.horizontalLayout_2.addWidget(self.checkbox_allow_thumbs)


        self.gridLayout.addLayout(self.horizontalLayout_2, 4, 0, 1, 1)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_3 = QLabel(Dialog)
        self.label_3.setObjectName(u"label_3")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy)

        self.horizontalLayout_3.addWidget(self.label_3)

        self.combo_thumb_plugin = QComboBox(Dialog)
        self.combo_thumb_plugin.setObjectName(u"combo_thumb_plugin")

        self.horizontalLayout_3.addWidget(self.combo_thumb_plugin)


        self.gridLayout.addLayout(self.horizontalLayout_3, 5, 0, 1, 1)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Ok)

        self.gridLayout.addWidget(self.buttonBox, 7, 0, 1, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.labelName = QLabel(Dialog)
        self.labelName.setObjectName(u"labelName")

        self.horizontalLayout.addWidget(self.labelName)

        self.catalog_path = QLineEdit(Dialog)
        self.catalog_path.setObjectName(u"catalog_path")

        self.horizontalLayout.addWidget(self.catalog_path)


        self.gridLayout.addLayout(self.horizontalLayout, 3, 0, 1, 1)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)

        self.label_info_configure = QLabel(Dialog)
        self.label_info_configure.setObjectName(u"label_info_configure")

        self.horizontalLayout_4.addWidget(self.label_info_configure)

        self.bt_configure = QPushButton(Dialog)
        self.bt_configure.setObjectName(u"bt_configure")

        self.horizontalLayout_4.addWidget(self.bt_configure)


        self.gridLayout.addLayout(self.horizontalLayout_4, 6, 0, 1, 1)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Catalog Settings", None))
        self.checkbox_allow_thumbs.setText(QCoreApplication.translate("Dialog", u"Allow Build Thumbnails", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", u"Thumbnail building plugin", None))
        self.labelName.setText(QCoreApplication.translate("Dialog", u"Path", None))
        self.label_info_configure.setText(QCoreApplication.translate("Dialog", u"Configure Info", None))
        self.bt_configure.setText(QCoreApplication.translate("Dialog", u"Configure ...", None))
    # retranslateUi

