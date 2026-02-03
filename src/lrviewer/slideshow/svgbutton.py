# pylint: disable=line-too-long,invalid-name
"""

Button width SVG Icon

modified from "https://github.com/SHADR1N/pyside6-svg-widgets"
"""
import re
from functools import partial
from typing import Optional, Union
from functools import lru_cache
import xml.etree.ElementTree as Et


from PySide6.QtWidgets import (
    QWidget,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import QTimer, QSize, Signal, QByteArray
from PySide6.QtSvgWidgets import QSvgWidget


@lru_cache()
def get_color(
    object_name,
    style_sheet,
    hover=False,
    pressed=False,
    checked=False,
    style_filter="icon-color",
):
    style_blocks = style_sheet.split("}")
    for block in style_blocks:

        if not object_name:
            continue

        _filter = any(
            [
                (f"{object_name}:hover") in block.strip(),
                (f"{object_name}:pressed" in block.strip()),
                (f"{object_name}:checked" in block.strip()),
            ]
        )
        if (
            not any([hover, pressed, checked])
            and object_name in block.strip()
            and not _filter
        ):
            style_rules = block.split("{")[-1].strip()

        elif hover and f"{object_name}:hover" in block.strip():
            style_rules = block.split("{")[-1].strip()

        elif checked and f"{object_name}:checked" in block.strip():
            style_rules = block.split("{")[-1].strip()

        elif pressed and f"{object_name}:pressed" in block.strip():
            style_rules = block.split("{")[-1].strip()

        else:
            continue

        clear = lambda e: str(e).replace("/*", "").replace("*/", "")
        style_string = "\n".join(
            [
                clear(i).strip()
                for i in style_rules.split("\n")
                if clear(i).strip().startswith(style_filter)
            ]
        )

        if style_string:
            pattern = style_filter + r":\s*([^;]+);"
            matches = re.findall(pattern, style_string)
            _match = matches[0] if matches else None
            return _match, style_sheet

    return None, None


def get_effective_style(
    init_widget: QWidget,
    hover=False,
    pressed=False,
    checked=False,
    style_filter="icon-color",
):
    """Get the effective style of a widget, considering parent styles."""

    object_name = type(init_widget).__name__
    current_widget = init_widget
    while current_widget:
        try:
            style_sheet = current_widget.styleSheet()
            if style_sheet and object_name in style_sheet:
                x, y = get_color(
                    object_name, style_sheet, hover, pressed, checked, style_filter
                )
                if x and y:
                    return x, y

            # Move to the parent widget
            current_widget = current_widget.parentWidget()

        except RuntimeError:
            break
    return None, None


class QSvgButtonIcon(QSvgWidget):
    """Svg Icon Button"""

    enter = Signal()
    leave = Signal()
    clicked = Signal()

    def __init__(self, svg_path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setContentsMargins(0, 0, 0, 0)
        self.size = (20, 20)
        self.stylecode = None
        self.closed = False
        self.tree = None
        self.root = None
        self.svg_path = None
        if self.setSvg(svg_path):
            self.svg_path = svg_path
        self.style_filter = "color"

    def event(self, e):
        super().event(e)
        if str(e.type()) == "Type.PaletteChange":
            self.leaveEvent(None)
        return True

    def setSvgSize(self, width: Union[int, QSize], height: Optional[int] = None):
        if isinstance(width, QSize):
            width, height = width.width(), width.height()

        self.setFixedSize(QSize(width, height))
        self.size = (width, height)
        self.leaveEvent(None)

    def setSvg(self, icon):
        try:
            self.tree = Et.parse(icon)
        except FileNotFoundError:
            return False
        self.root = self.tree.getroot()
        self.svg_path = icon
        QTimer.singleShot(100, partial(self.leaveEvent, None))
        return True

    def updateIcon(self, color):
        """update icon path

        color syntax #10ff00ff : alpha-R-G-B
        """
        if not color or not self.svg_path:
            return
        col = QColor(color)
        alpha = col.alphaF()
        alpha = f"{float(alpha):.1f}"
        paths = self.root.findall(".//{*}path")
        paths2 = self.root.findall(".//{*}svg")
        for path in paths + paths2:
            path.set("fill-opacity", alpha)
            path.set("fill", col.name())

        self.load(self.get_QByteArray())
        self.setFixedSize(*self.size)

    def get_QByteArray(self):
        xmlstr = Et.tostring(self.root, encoding="utf8", method="xml")
        return QByteArray(xmlstr)

    def enterEvent(self, event):
        self.enter.emit()
        effective_style, self.stylecode = get_effective_style(
            self, hover=True, style_filter=self.style_filter
        )
        self.updateIcon(effective_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.closed:
            if event:
                event.ignore()
            return

        self.leave.emit()
        effective_style, self.stylecode = get_effective_style(
            self, style_filter=self.style_filter
        )
        self.updateIcon(effective_style)
        if event:
            super().leaveEvent(event)

    def mousePressEvent(self, event):
        effective_style, self.stylecode = get_effective_style(self, pressed=True)
        self.updateIcon(effective_style)
        super().mousePressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed = True

    def deleteLater(self):
        super().deleteLater()
        self.closed = True

    def mouseReleaseEvent(self, event):
        if self.underMouse():
            effective_style, self.stylecode = get_effective_style(self, hover=True)
        else:
            effective_style, self.stylecode = get_effective_style(self)

        self.updateIcon(effective_style)
        super().mouseReleaseEvent(event)
        self.clicked.emit()
