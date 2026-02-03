# -*- encoding: utf-8 -*-

"""

Metadatas viewer

"""

import logging

from qt_json_view.model import JsonModel
from qt_json_view.view import JsonView


from lrApi import PhotoMetadatas


log = logging.getLogger(__name__)


class MetadatasView(JsonView):
    """Metadatas view bases on TreeView"""

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def setMetadatas(self, photo_metadatas: PhotoMetadatas):
        """set metadatas in widget"""
        self.setModel(
            JsonModel(
                data={} if photo_metadatas is None else photo_metadatas.metadatas()
            )
        )
