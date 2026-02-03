# -*- encoding: utf-8 -*-
# pylint: disable=line-too-long,invalid-name

"""

Thumbs provider

"""

import os
from enum import Enum
import logging

from PySide6.QtGui import (
    QImage,
    QPixmap,
    QTransform,
)

from lrprev import (
    LRPrevFile,
    LRPreviewsDB,
    LRPixelsDB,
    LRPrevException,
)

log = logging.getLogger(__name__)


class FromDB(Enum):
    """thumbnail source"""

    ROOTPIXELS = 1
    PREVIEWS = 2


class ThumbsProvider:
    """
    Get thumbnails from various sources
    """

    def __init__(self):
        """constructor"""
        self.prevdb = None
        self.pixelsdb = None
        # self.from_db = FromDB.ROOTPIXELS
        self.from_db = None
        self.thumb_level = None
        self.has_thumbs = None

    def open_provider(
        self, lrcat_file, from_db: FromDB = FromDB.PREVIEWS, level: str = "3"
    ):
        """constructor"""
        # close previous databases
        if self.pixelsdb:
            self.pixelsdb.close()
            self.pixelsdb = None
        if self.prevdb:
            self.prevdb.close()
            del self.prevdb
            self.prevdb = None

        self.from_db = from_db
        self.thumb_level = level
        base, _ = os.path.splitext(lrcat_file)
        previews_path = f"{base} Previews.lrdata"
        self.has_thumbs = True
        if os.path.exists(previews_path):
            try:
                # open rootpixels database
                self.pixelsdb = LRPixelsDB(
                    os.path.join(previews_path, "root-pixels.db")
                )
            except LRPrevException as _e:
                log.error(_e)
                self.has_thumbs = False
            try:
                # open previews database
                self.prevdb = LRPreviewsDB(os.path.join(previews_path, "previews.db"))
            except LRPrevException as _e:
                log.error(_e)
        else:
            log.error('No directory "%s"', previews_path)
            self.has_thumbs = False

    def _thumb_from_rootpixels(self, lr_id: int) -> QPixmap:
        """return thum from rootpixels.db"""
        if self.prevdb is None:
            return QPixmap()
        try:
            uuid, orientation = self.prevdb.get_uuid_orient(lr_id)
        except LRPrevException:
            log.debug("no preview file from prevdb")
            return QPixmap()
        try:
            data_rows = self.pixelsdb.get_datas(uuid)
        except LRPrevException:
            log.info("no preview file")
            return QPixmap()
        log.debug("%s thumbnail(s) available", len(data_rows))
        jpeg_datas, color_profile, cropped_width, cropped_height, quality = data_rows[0]
        return self._transform(jpeg_datas, orientation)

    def _thumb_from_previews(self, lr_id: int, level: str) -> QPixmap:
        """return thum from prev file"""
        if self.prevdb is None:
            return QPixmap()
        try:
            fname_preview, orientation = self.prevdb.get_prev_infos(lr_id)
        except LRPrevException as _e:
            log.warning(_e)
            return QPixmap()

        # open/decode preview file
        prev = LRPrevFile(fname_preview)
        datas = prev.load("header").decode()[10:]
        try:
            if level.lower() == "max":
                thumb_level = prev.sections[-1]
            elif level.startswith(">"):
                size = int(level[1:])
                for num, (width, height) in enumerate(prev.level_sizes()):
                    if height > size and width > size:
                        thumb_level = f"level_{num + 1}"
                        break
            else:
                thumb_level = f"level_{level}"
            datas = prev.load(thumb_level)
        except KeyError:
            log.warning("prev has no datas")
            return QPixmap()
        width, height = prev.level_sizes(thumb_level)
        # log.info('  selected level: %s (%s x %s). image datas: %s bytes', thumb_level, width, height, len(datas))

        return self._transform(datas, orientation)

    def _transform(self, datas: any, orientation: str = "AB") -> QPixmap:
        """convert jpeg datas to pixmap, transform for orientation"""
        image = QImage.fromData(datas)
        # note: tranform order is important
        transform = QTransform()
        if orientation == "AB":  # exif orientation = 1
            pass
        elif orientation == "BA":  # exif orientation = 2
            transform.scale(-1, 1)
        elif orientation == "CD":  # exif orientation = 3
            transform.rotate(180)
        elif orientation == "DC":  # exif orientation = 4
            transform.scale(-1, 1)
            transform.rotate(180)
        elif orientation == "CB":  # exif orientation = 5
            transform.scale(-1, 1)
            transform.rotate(90)
        elif orientation == "BC":  # exif orientation = 6
            transform.rotate(90)
        elif orientation == "AD":  # exif orientation = 7
            transform.scale(-1, 1)
            transform.rotate(270)
        elif orientation == "DA":  # exif orientation = 8
            transform.rotate(270)
        else:
            log.error("Bad orientation")
            return QPixmap()

        if not transform.isIdentity():
            image = image.transformed(transform)
        return QPixmap.fromImage(image)

    def get_thumb(self, lr_id: int, level="3"):
        """
        return thumbnail
        """
        if level == "0" or self.from_db == FromDB.ROOTPIXELS:
            return self._thumb_from_rootpixels(lr_id)

        if self.from_db == FromDB.PREVIEWS:
            return self._thumb_from_previews(lr_id, level)


#
# create global instance
#
thumbs_provider = ThumbsProvider()
