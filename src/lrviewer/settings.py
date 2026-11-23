"""

Settings access for lrviewer

"""

from PySide6.QtCore import QSettings

# app name and version
APP_NAME = "Lightroom Viewer"
APP_VERSION = "2026.11.13"


def settings_base_catalog(catalog_path):
    """
    Return tuple :
        (
        existing_settings,
        settings base path from catalog path
        )
    """
    used_catalog_ids = set()
    settings.beginGroup("knownCatalogs")
    for catalog_id in settings.childGroups():
        settings.beginGroup(catalog_id)
        path = settings.value("path", "")
        settings.endGroup()
        if path == catalog_path:
            settings.endGroup()
            return (True, f"knownCatalogs/{catalog_id}")
        used_catalog_ids.add(int(catalog_id))
    settings.endGroup()

    # Now find the first integer > 0 not in used_catalog_ids
    i = 1
    while i in used_catalog_ids:
        i += 1
    return (False, f"knownCatalogs/{i}")


# QSettings for this application
settings = QSettings("fdenivac", "Lightroom Viewer")
