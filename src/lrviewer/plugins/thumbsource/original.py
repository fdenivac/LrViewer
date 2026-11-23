"""

a kind of plugin retrieving source image filename to use for build thumbnail

"""

from plugins.thumbsource.plugin_thumbsource import ThumbSource


class Original(ThumbSource):
    """Thumb source is original photo filename"""

    _alias_ = "original"
    description = "[original] Thumb from original"

    def __init__(self, settings_path):
        self.settings_path = settings_path

    def thumb_source(self, lr_id, date_capture, original_filename, copy_name):
        """
        return source photo filename to use for build thumbnail

        Here, return original filename
        """
        return original_filename

    def write_settings(self):
        """write config to registry"""

    def has_configure_dialog(self):
        """return True if plugin has configure fonction"""
        return False

    def configure(self):
        """configure plugin : store settings"""
        return True
