# -*- encoding: utf-8 -*-
# pylint: disable=line-too-long,invalid-name

"""

Thumbs provider : generic access to thumbnails

- read/write LR preview files
- write thumb level_1 in root-pixels.db (compatibility with Lightroom)
"""

import os
from enum import Enum
from datetime import datetime
import logging
from threading import Lock

from PySide6.QtCore import (
    QObject,
    QThreadPool,
    QThread,
    QRunnable,
    Signal,
    QModelIndex,
    Slot,
)

from PySide6.QtGui import (
    QImage,
    QPixmap,
    QTransform,
)

import pluginlib
from lrtools.lrcat import lr_strptime

from settings import settings, settings_base_catalog
from lrprev import (
    LRPrevFile,
    LRPrevFileWriter,
    LRPreviewsDB,
    LRPrevException,
)
from rootpixels import LRPixelsDB
from lrApi import lr_api
from thumbBuilder import ThumbBuilder
from utils import FifoList

log = logging.getLogger(__name__)


class FromDB(Enum):
    """thumbnail source"""

    ROOTPIXELS = 1
    PREVIEWS = 2


class ThumbException(Exception):
    """ThumbException generic Exception"""


class WorkerSignals(QObject):
    """Signals for thumb worker thread"""

    started = Signal(QModelIndex, int)
    finished = Signal(QModelIndex, int)
    error = Signal(str)


class ThumbWorker(QRunnable):
    """Worker thread : create preview from image"""

    def __init__(self, parent, lr_id, row, filename, source):
        super().__init__()
        self.parent = parent
        self.lr_id = lr_id
        self.row = row
        self.filename = filename
        self.signals = self.parent.signals
        self.source = source

    @Slot()
    def run(self):
        try:
            self.signals.started.emit(self.source, self.lr_id)
            self.parent._create_thumbnail(self.lr_id, self.row, self.filename)
        except ThumbException as _e:
            self.signals.error.emit(_e)
            log.error("Thread Exception id:%d", self.lr_id)
        else:
            self.signals.finished.emit(self.source, self.lr_id)
            with self.parent.building_lock:
                del self.parent.images_building[self.lr_id]


class ThumbsProvider(QObject):
    """
    Get thumbnails from various sources
    """

    def __init__(self):
        """constructor"""
        self.prevdb = None
        self.pixelsdb = None
        self.from_db = None
        self.has_thumbs = None
        self.previews_path = ""
        self._allow_append = False
        self.images_building = {}
        self._allow_reuse_lrprev = True
        self.signals = WorkerSignals()
        self.building_lock = Lock()
        self.threadpool = QThreadPool()
        self.threadpool.setThreadPriority(QThread.Priority.LowestPriority)
        nThreads = settings.value(
            "thumbMaxThreads", self.threadpool.maxThreadCount() / 2, type=int
        )
        self.threadpool.setMaxThreadCount(nThreads)
        log.info(
            "Multithreading with maximum %s threads", self.threadpool.maxThreadCount()
        )
        self.plugin_thumbsource = None
        self.sources_missing = FifoList(
            5000
        )  # avoid re-check source availability and logging

    def open_provider(self, lrcat_file):
        """(re)open thumbnails provider"""
        self.from_db = FromDB.PREVIEWS

        # close previous databases
        if self.pixelsdb:
            self.pixelsdb.close()
            self.pixelsdb = None
        if self.prevdb:
            self.prevdb.close()
            del self.prevdb
            self.prevdb = None

        existing_setting, settings_path = settings_base_catalog(lrcat_file)
        assert existing_setting
        self._allow_append = settings.value(f"{settings_path}/allowThumbsAppend", False)

        base, _ = os.path.splitext(lrcat_file)
        self.previews_path = f"{base} Previews.lrdata"
        self.has_thumbs = True
        # create databases if needed
        if self._allow_append and (
            not os.path.exists(self.previews_path)
            or not os.path.exists(os.path.join(self.previews_path, "root-pixels.db"))
            or not os.path.exists(os.path.join(self.previews_path, "previews.db"))
        ):
            log.info(
                'No previews directory or no databases found in "%s" : create them',
                self.previews_path,
            )
            self.create_databases()

        # open previews database
        if os.path.exists(self.previews_path):
            try:
                # open rootpixels database
                self.pixelsdb = LRPixelsDB(
                    os.path.join(self.previews_path, "root-pixels.db"),
                    open_options="mode=rw" if self._allow_append else "mode=ro",
                )
            except LRPrevException as _e:
                self.pixelsdb = None
                self.has_thumbs = False
                log.error(_e)
            try:
                # open previews database
                self.prevdb = LRPreviewsDB(
                    os.path.join(self.previews_path, "previews.db"),
                    open_options="mode=rw" if self._allow_append else "mode=ro",
                )
            except LRPrevException as _e:
                self.prevdb = None
                log.error(_e)
        else:
            log.error('No directory "%s"', self.previews_path)
            self.has_thumbs = False

        # set plugin source
        """init plugin thumb source"""
        plugin_name = settings.value(f"{settings_path}/plugin", "original")
        log.info(
            "plugin_name is %s (from settings %s)",
            plugin_name,
            f"{settings_path}/plugin",
        )
        loader = pluginlib.PluginLoader(modules=["plugins.thumbsource"])
        plugin_class = loader.get_plugin("thumbsource", plugin_name)
        self.plugin_thumbsource = plugin_class(settings_path)

    def has_rootpixelsdb(self):
        """check root-pixels.db available"""
        return self.pixelsdb is not None

    def has_previewsdb(self):
        """check previews.db available"""
        return self.prevdb is not None

    def allow_append(self):
        """return True if allow thumbnails append"""
        return self._allow_append

    def set_previews_path(self, path):
        """set/change previews path"""
        self.previews_path = path

    def count_thumbnails_building(self):
        """return count of thumnail to build"""
        with self.building_lock:
            return len(self.images_building)

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

    def _thumb_from_previews(
        self, lr_id: int, level: str, source: QModelIndex, use_thread=True
    ) -> QPixmap:
        """return thum from prev file"""
        if self.prevdb is None:
            return QPixmap()
        try:
            fname_preview, orientation = self.prevdb.get_prev_infos(lr_id)
        except LRPrevException as _e:
            if _e.args[0] == "no data":
                if not self._allow_append:
                    return QPixmap()
                exists, row, filename_image = self._get_build_infos(lr_id)
                if not exists:
                    return QPixmap()
                if use_thread:
                    worker = ThumbWorker(self, lr_id, row, filename_image, source)
                    with self.building_lock:
                        if lr_id in self.images_building:
                            log.warning("Already building image %s", lr_id)
                            return QPixmap()
                        self.images_building[worker.lr_id] = lr_id
                    self.threadpool.start(worker)
                    return QPixmap()
                if not self._create_thumbnail(lr_id, row, filename_image):
                    return QPixmap()
                fname_preview, orientation = self.prevdb.get_prev_infos(lr_id)
            else:
                log.error("LRPrevException %s", _e)
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
                if level == "0":
                    # TODO : test when no root-pixels db not used
                    level = 1
                thumb_level = f"level_{level}"
            datas = prev.load(thumb_level)
        except KeyError:
            log.warning("prev has no datas")
            return QPixmap()
        width, height = prev.level_sizes(thumb_level)

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

    def get_thumb(self, lr_id: int, level="3", source=None, use_thread=True):
        """
        return thumbnail from Adobe_images.id_local
        level : pyramid level
        source : QModelIndex to repaint
        use_thread : if True use worker thread and signal avaibility, else return image immediately
        """
        # TODO comment following code for test : don't use ROOTPIXELS
        # if level == "0" or self.from_db == FromDB.ROOTPIXELS:
        #     return self._thumb_from_rootpixels(lr_id)

        if self.from_db == FromDB.PREVIEWS:
            return self._thumb_from_previews(lr_id, level, source, use_thread)

        return QPixmap()

    def _get_build_infos(self, lr_id):
        """
        get infos needed for build thumb from LR database
        """
        row = lr_api.api.lrphoto.select_generic(
            "datecapt,name=full,vname,uuidfile,digest,cropwidth,cropheight,width,height,orientation",
            f"id={lr_id}",
        ).fetchone()

        datecapt, fname, copyname = row[:3]
        if datecapt:
            dt_datecapt = lr_strptime(datecapt)
        else:
            dt_datecapt = datetime.strptime("1900-01-01T00:00:00", "%Y-%m-%dT%H:%M:%S")

        # call plugin retrieving photo filename for building thumbnail
        source_filename = self.plugin_thumbsource.thumb_source(
            lr_id, dt_datecapt, fname, copyname
        )
        if self.sources_missing.exists(lr_id):
            return False, None, None
        if not os.path.exists(source_filename):
            log.warning("No source for thumb : %s", source_filename)
            self.sources_missing.append(lr_id)
            return False, None, None
        return True, row, source_filename

    def _create_thumbnail(self, lr_id, row, image_source):
        """
        create thumbnails and lrprev file

        We need :
            - basic infos needed by lrprev file uuidfile, digest, cropped width and height
            - image file name
              in case of this image

        """
        (
            datecapt,
            fname,
            copyname,
            uuidfile,
            digest,
            crop_width,
            crop_height,
            width,
            height,
            orientation,
        ) = row

        if crop_width != "uncropped":
            if crop_width is None:
                raise ThumbException(f"crop_width is None for {fname}{copyname}")
            width = int(crop_width)
            height = int(crop_height)
        else:
            width = int(width)
            height = int(height)

        # build lrprev files
        lrprev = LRPrevFileWriter(
            uuid=uuidfile,
            digest=digest,
            cropped_width=width,
            cropped_height=height,
        )
        lrprev_fname = os.path.join(self.previews_path, lrprev.standard_pathname())
        # no re-create prev file on option
        if not self._allow_reuse_lrprev or not os.path.exists(lrprev_fname):
            builder = ThumbBuilder(lrprev)
            try:
                builder.build_thumbs(image_source, orientation=orientation)
            except FileNotFoundError as _e:
                raise ThumbException(f"FAILED to open '{image_source}'") from _e
            lrprev_fname = os.path.join(self.previews_path, lrprev.standard_pathname())
            dirs, _ = os.path.split(lrprev_fname)
            os.makedirs(dirs, exist_ok=True)
            lrprev.write(lrprev_fname)
        else:
            log.warning("Prev file already exists : reuse it")

        # insert datas in databases
        try:
            prevdb = LRPreviewsDB(
                os.path.join(self.previews_path, "previews.db"),
                open_options="mode=rw",
            )
            prevdb.insert_datas(lr_id, uuidfile, digest, orientation)
            prevdb.close()
        except LRPrevException as _e:
            log.error(_e)
        try:
            pixelsdb = LRPixelsDB(
                os.path.join(self.previews_path, "root-pixels.db"),
                open_options="mode=rw",
            )
            lrprev = LRPrevFile(lrprev_fname)
            jpeg_datas = lrprev.load("level_1")
            pixelsdb.insert_datas(
                uuidfile, digest, jpeg_datas, "sRGB", width, height, "standard"
            )
            pixelsdb.close()
        except LRPrevException as _e:
            log.error(_e)

    def create_databases(self):
        """
        create databases root-pixels.db and previews.db
        """
        # TODO
        self.prevdb = LRPreviewsDB.create(
            os.path.join(self.previews_path, "previews.db")
        )
        self.pixelsdb = LRPixelsDB.create(
            os.path.join(self.previews_path, "root-pixels.db")
        )


#
# create global instance
#
thumbs_provider = ThumbsProvider()
