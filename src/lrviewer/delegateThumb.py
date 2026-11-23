# -*- encoding: utf-8 -*-
## pylint: disable=too-many-lines,disable=line-too-long,invalid-name

"""

QStyledItemDelegate for PhotosThumbView (QTableView)

"""

from __future__ import annotations
import os
import logging

from PySide6.QtCore import (
    Qt,
    QModelIndex,
    QRect,
    QSize,
)

from PySide6.QtWidgets import (
    QStyleOptionViewItem,
    QStyledItemDelegate,
    QStyle,
)
from PySide6.QtGui import (
    QPainter,
    QPixmap,
    QIcon,
    QGuiApplication,
    QColor,
    QFont,
)

from settings import settings
from lrApi import lr_api
from thumbProvider import thumbs_provider

CELL_PADDING = 0
TEXT_HEIGHT = 20

# logger
log = logging.getLogger(__name__)


def abspath(filename):
    return os.path.join(os.path.realpath(os.path.dirname(__file__)), filename)


class ThumbDelegate(QStyledItemDelegate):
    """
    delegate for PhotosThumbView (QTableView):
    """

    def __init__(self, cell_size, parent):
        super().__init__(parent)
        self.cell_size = cell_size

        self.color_cur: QColor = QGuiApplication.palette().highlight().color()
        self.color_sel = QColor(self.color_cur)
        self.color_sel.setAlpha(160)
        self.font = QFont(
            settings.value("fontThumbView", "Microsoft Sans Serif"),
            settings.value("fontsizeThumbView", 7),
        )
        icon = QIcon(abspath("./ico/mark_hasgps.png"))
        self.pixmap_has_gps = icon.pixmap(icon.availableSizes()[0])
        icon = QIcon(abspath("./ico/mark_hascollection.png"))
        self.pixmap_has_collection = icon.pixmap(icon.availableSizes()[0])
        icon = QIcon(abspath("./ico/mark_haskeyword.png"))
        self.pixmap_has_keyword = icon.pixmap(icon.availableSizes()[0])
        self.pixmap_rating = []
        for i in range(1, 6):
            icon = QIcon(abspath("./ico/mark_rating_" + str(i) + ".png"))
            self.pixmap_rating.append(icon.pixmap(icon.availableSizes()[0]))
        self.use_markers = settings.value("useIconMarkersInThumbView", True)
        if self.use_markers:
            lr_api.add_hidden_columns("hasgps,hascollection,haskeyword,rating")

    def paint(
        self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex
    ):
        """paint cell"""
        painter.save()
        painter.setFont(self.font)
        row = index.row()
        # option.rect holds the area we are painting on the widget (a cell)
        if option.state & QStyle.StateFlag.State_Selected:
            pixmap = QPixmap(option.rect.width(), option.rect.height())
            index_cur = self.parent().currentIndex()
            color = self.color_cur if row == index_cur.row() else self.color_sel
            pixmap.fill(color)
            painter.drawPixmap(option.rect, pixmap)

        # draw image
        #
        pixmap = None
        col_id = lr_api.column_index("id")
        if col_id >= 0:
            photo_id = lr_api.query_result(row, col_id, visible_col=False)
            pixmap = thumbs_provider.get_thumb(photo_id, level="3", source=index)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    option.rect.width(),
                    option.rect.height() - TEXT_HEIGHT,
                    aspectMode=Qt.AspectRatioMode.KeepAspectRatio,
                )
        else:
            pixmap = QPixmap()
        if not pixmap.isNull():
            # Position in the middle of the area.
            size = pixmap.size()
            adjust_top = (option.rect.height() - TEXT_HEIGHT - size.height()) // 2
            adjust_left = (option.rect.height() - size.width()) // 2
            imageRect = QRect(
                option.rect.left() + adjust_left,
                option.rect.top() + adjust_top,
                size.width(),
                size.height(),
            )
            painter.drawPixmap(imageRect, pixmap)
        else:
            imageRect = QRect(
                option.rect.left(),
                option.rect.top(),
                option.rect.width(),
                option.rect.height() - TEXT_HEIGHT,
            )

        # Draw icon markers on photo
        if self.use_markers:
            col_has_gps = lr_api.column_index("hasgps")
            col_has_collection = lr_api.column_index("hascollection")
            col_has_keyword = lr_api.column_index("haskeyword")
            col_rating = lr_api.column_index("rating")
        else:
            col_has_gps = col_has_collection = col_has_keyword = col_rating = -1

        def _rect_mark(pixmap):
            """return position pixmap"""
            return QRect(
                imageRect.right() - pixmap.width(),
                imageRect.bottom() - pixmap.height(),
                pixmap.width(),
                pixmap.height(),
            )

        if col_has_gps >= 0 and lr_api.query_result(
            row, col_has_gps, visible_col=False, raw=True
        ):
            icon_rect = _rect_mark(self.pixmap_has_gps)
            painter.drawPixmap(icon_rect, self.pixmap_has_gps)
            imageRect.setRight(imageRect.right() - self.pixmap_has_gps.width())

        if col_has_collection >= 0 and lr_api.query_result(
            row, col_has_collection, visible_col=False, raw=True
        ):
            icon_rect = _rect_mark(self.pixmap_has_collection)
            painter.drawPixmap(icon_rect, self.pixmap_has_collection)
            imageRect.setRight(imageRect.right() - self.pixmap_has_collection.width())

        if col_has_keyword >= 0 and lr_api.query_result(
            row, col_has_keyword, visible_col=False, raw=True
        ):
            icon_rect = _rect_mark(self.pixmap_has_keyword)
            painter.drawPixmap(icon_rect, self.pixmap_has_keyword)
            imageRect.setRight(imageRect.right() - self.pixmap_has_keyword.width())

        if col_rating >= 0:
            try:
                rating = int(lr_api.query_result(row, col_rating, visible_col=False))
                if rating <= 0 or rating > 5:
                    raise ValueError
                pixmap = self.pixmap_rating[rating - 1]
                icon_rect = _rect_mark(pixmap)
                painter.drawPixmap(icon_rect, pixmap)
                imageRect.setRight(imageRect.right() - pixmap.width())
            except (TypeError, ValueError):
                pass

        # Draw the filename under image
        col_id = lr_api.column_index("name")
        if col_id >= 0:
            text = lr_api.query_result(row, col_id, visible_col=False)
            txt_rect = QRect(
                option.rect.x(),
                option.rect.y() + option.rect.height() - TEXT_HEIGHT,
                option.rect.width(),
                TEXT_HEIGHT,
            )
            painter.drawText(
                txt_rect,
                Qt.AlignmentFlag.AlignCenter,
                text,
            )

        painter.restore()

    def sizeHint(
        self,
        options: QStyleOptionViewItem,  # pylint: disable=unused-argument
        index: QModelIndex,  # pylint: disable=unused-argument
    ):
        """sizeHint define cell size : all items has same size"""
        return QSize(self.cell_size, self.cell_size)
