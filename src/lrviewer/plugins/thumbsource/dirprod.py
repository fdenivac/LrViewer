"""
plugin retrieving source image filename to use for build thumbnail
"""

import os

from settings import settings
from plugins.thumbsource.plugin_thumbsource import ThumbSource
from plugins.thumbsource.dirprod_dlg import ConfigDialog


class DirProd(ThumbSource):
    """Thumb source filename location is based on date"""

    _alias_ = "dir_prod"
    description = "[dir_prod] Thumb from production directory based on date"

    def __init__(self, settings_path):
        self.settings_path = settings_path
        self.prod_dir = self.date_format = None
        self.read_settings()
        super().__init__()

    def thumb_source(self, lr_id, date_capture, original_filename, copy_name):
        """
        return source photo filename to use for build thumbnail

        Here, suppose that all photos are :
            - developed in JPEG
            - stored in specific root directory, sorted in sub-directories using YEAR/MONTH (format="%Y/%m")

        ex:
            ROOT_DIR
                2000
                    01
                    10
                2005
                    02
                    12
        """

        if self.prod_dir is None:
            self.read_settings()
        # path with sub-directories based on year and month of capture :
        #   "../<YEAR>/<MONTH>/.."
        prodpath = os.path.normpath(
            os.path.join(self.prod_dir, date_capture.strftime(self.date_format))
        )

        # extract base without path nor extension
        _, basename = os.path.split(original_filename)
        basename, _ = os.path.splitext(basename)

        # final filename in production directory
        if copy_name is None:
            copy_name = ""
        prodname = os.path.join(
            prodpath,
            f"{basename}{copy_name}.jpg",
        )
        return prodname

    def read_settings(self):
        """read config from registry"""
        self.prod_dir = settings.value(f"{self.settings_path}/{self._alias_}_directory")
        self.date_format = settings.value(f"{self.settings_path}/{self._alias_}_format")

    def write_settings(self):
        """write config to registry"""
        settings.setValue(
            f"{self.settings_path}/{self._alias_}_directory", self.prod_dir
        )
        settings.setValue(
            f"{self.settings_path}/{self._alias_}_format", self.date_format
        )

    def has_configure_dialog(self):
        """return True if plugin has configure fonction"""
        return True

    def configure(self):
        """configure plugin : store settings"""
        dialog = ConfigDialog(self.prod_dir, self.date_format, None)
        ret = dialog.exec()
        if ret:
            self.prod_dir = dialog.ui.prod_dir.text()
            self.date_format = dialog.ui.date_format.text()
        return ret
