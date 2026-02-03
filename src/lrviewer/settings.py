"""

Settings access for lrviewer

"""

from PySide6.QtCore import QSettings


# sort and filter
USE_SORT_LIST_MODEL = False

# app name and version
APP_NAME = "Lightroom Viewer"
APP_VERSION = "2026.2.3"


settings = QSettings("fdenivac", "Lightroom Viewer")
