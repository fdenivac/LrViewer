"""
plugin parent for thumbsource
"""

import pluginlib


@pluginlib.Parent("thumbsource")
class ThumbSource:

    @pluginlib.abstractmethod
    def thumb_source(self, lr_id, date_capture, original_filename, copy_name):
        """return thumb source filename"""

    @pluginlib.abstractmethod
    def configure(self):
        """configure plugin : store settings"""

    @pluginlib.abstractmethod
    def has_configure_dialog(self):
        """return True if plugin has configure fonction"""

    @pluginlib.abstractmethod
    def write_settings(self):
        """write settings to registry"""
