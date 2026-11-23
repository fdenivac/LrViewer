from PySide6.QtWidgets import (
    QDialog,
    QListWidgetItem,
    QMessageBox,
)
from PySide6.QtCore import (
    Qt,
    Signal,
)

import pluginlib

from settings import settings, settings_base_catalog

from utils import avail_plugins_thumbsource
from ui.catalog_settings_ui import Ui_Dialog as UiCatalogSettingsDialog
from ui.catalogs_manage_ui import Ui_Dialog as UiCatalogsManageDialog
from lrApi import lr_api

DEFAULT_PLUGIN = "original"


class CatalogManagerDialog(QDialog):

    # signal for reconfig thumbsProvider
    catalogSettingsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = UiCatalogsManageDialog()
        self.ui.setupUi(self)

        self.current_catalog_id = None
        self._load_catalogs_to_list()
        self.ui.list_catalogs.currentItemChanged.connect(self.on_catalog_selected)
        self.ui.list_catalogs.itemDoubleClicked.connect(self.on_catalog_double_clicked)
        self.ui.bt_configure.clicked.connect(self.onConfigure)
        self.ui.bt_delete.clicked.connect(self.onDelete)

    def on_catalog_selected(self, current_item, previous_item):
        if not current_item:
            self.current_catalog_id = None
            return
        catalog_id = current_item.data(Qt.ItemDataRole.UserRole)
        self.current_catalog_id = catalog_id

    def on_catalog_double_clicked(self, item):
        if not item:
            return
        self._edit_settings(item)

    def onConfigure(self):
        if not self.current_catalog_id:
            return
        item = self.ui.list_catalogs.currentItem()
        if not item:
            return
        self._edit_settings(item)

    def _edit_settings(self, item):
        filename = item.text()
        _, settings_path = settings_base_catalog(filename)
        dlg = CatalogSettingsDialog(filename, settings_path, parent=self)
        dlg.exec()

    def onDelete(self):
        if not self.current_catalog_id:
            return

        reply = QMessageBox.question(
            self,
            "Confirm catalog delete",
            f"Would you really like to delete the catalog'{self.current_catalog_id}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            settings.beginGroup("KnownCatalogs")
            settings.remove(self.current_catalog_id)
            settings.endGroup()

            self._load_catalogs_to_list()
            self.on_catalog_selected(None, None)

    def _load_catalogs_to_list(self):
        self.ui.list_catalogs.clear()
        settings.beginGroup("KnownCatalogs")
        for catalog_id in settings.childGroups():
            item = QListWidgetItem(settings.value(f"{catalog_id}/path", "Unknown"))
            item.setData(Qt.ItemDataRole.UserRole, catalog_id)
            self.ui.list_catalogs.addItem(item)
        settings.endGroup()


class CatalogSettingsDialog(QDialog):
    """Dialog catalog settings"""

    def __init__(self, catalog_path, settings_path, allow_cancel=True, parent=None):
        super().__init__(parent)
        self.settings_path = settings_path
        self.allow_cancel = allow_cancel
        self.parent = parent

        # remove window close button
        if not self.allow_cancel:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        # create plugins instance in dictionary
        self.plugins = {}
        loader = pluginlib.PluginLoader(modules=["plugins.thumbsource"])
        plugins = avail_plugins_thumbsource()
        for plugin_name, _ in plugins:
            plugin_class = loader.get_plugin("thumbsource", plugin_name)
            plugin = plugin_class(self.settings_path)
            self.plugins[plugin_name] = plugin

        self.ui = UiCatalogSettingsDialog()
        self.ui.setupUi(self)

        self.ui.catalog_path.setText(catalog_path)
        self.ui.catalog_path.setEnabled(False)

        self.ui.checkbox_allow_thumbs.checkStateChanged.connect(self.onCheckAllowThumbs)
        self.ui.checkbox_allow_thumbs.setChecked(False)
        self.ui.combo_thumb_plugin.setEnabled(False)

        self.ui.bt_configure.clicked.connect(self.onConfigure)

        self._load_plugins_to_combo()
        self.ui.combo_thumb_plugin.setEnabled(False)
        self.ui.combo_thumb_plugin.currentIndexChanged.connect(
            self.onComboThumbPluginChanged
        )
        self._read_settings()

    def _load_plugins_to_combo(self):
        plugins = avail_plugins_thumbsource()
        self.ui.combo_thumb_plugin.clear()
        for index, plugin in enumerate(plugins):
            self.ui.combo_thumb_plugin.addItem(
                plugin[1],  # description
                plugin[0],  # name in setData
            )

    def _read_settings(self):
        """ " read settings

        catalog_path not read from settings : already in constructor
        """
        settings.beginGroup(self.settings_path)
        allow_thumbs = settings.value("allowThumbsAppend", True, type=bool)
        plugin = settings.value("plugin", DEFAULT_PLUGIN, type=str)
        settings.endGroup()
        self.ui.checkbox_allow_thumbs.setChecked(allow_thumbs)
        self.ui.combo_thumb_plugin.setCurrentIndex(
            self.ui.combo_thumb_plugin.findData(plugin)
        )

    def onComboThumbPluginChanged(self, index):
        plugin_name = self.ui.combo_thumb_plugin.currentData()
        self.ui.bt_configure.setEnabled(
            plugin_name is None or self.plugins[plugin_name].has_configure_dialog()
        )

    def onConfigure(self, checked):
        """Configure the selected thumbnail plugin"""
        plugin_name = self.ui.combo_thumb_plugin.currentData()
        self.plugins[plugin_name].configure()

    def onCheckAllowThumbs(self, state):
        if state == Qt.CheckState.Unchecked:
            self.ui.combo_thumb_plugin.setEnabled(False)
            self.ui.bt_configure.setEnabled(False)
        else:
            self.ui.combo_thumb_plugin.setEnabled(True)
            self.onComboThumbPluginChanged(self.ui.combo_thumb_plugin.currentIndex())

    def apply_settings(self):
        path = self.ui.catalog_path.text()
        allow_thumbs = self.ui.checkbox_allow_thumbs.isChecked()
        plugin_name = self.ui.combo_thumb_plugin.currentData()
        settings.beginGroup(self.settings_path)
        settings.setValue("path", path)
        settings.setValue("allowThumbsAppend", int(allow_thumbs))
        settings.setValue("plugin", plugin_name)
        settings.endGroup()
        # write settings for this plugin
        self.plugins[plugin_name].write_settings()
        # send signal to reconfigure current catalog
        if path == lr_api.catalog_path():
            self.parent.catalogSettingsChanged.emit()

    def accept(self):
        self.apply_settings()
        return super().accept()

    def reject(self):
        if self.allow_cancel:
            return super().reject()
