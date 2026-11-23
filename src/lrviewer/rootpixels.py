# -*- encoding: utf-8 -*-
# pylint: disable=line-too-long

"""
Access to root-pixels database of Lightroom catalog

class LRPixelsDB :
    Manage "root-pixels.db" Lightroom database
    Thumbnails are stored in database

    "quality" field is  (on +/-140000 photos):
        bigThumbnail        (3389 entries, width 61, 64, 94, 101)
        final               (12043 entries, width from 60 to 119)
        full                (8 entries, width 60 to 118)
        smallRender         (1416 entries, max width = 60)
        standard            (71188 entries, max width = 60)
        thumbnail           (14020 entries, width from 60 to 119)

Structure
    - uuid : from AgLibraryFile.id_global
    - from Adobe_imageDevelopSettings.digest
"""

import os
import sqlite3
import logging

from lrprev import LRPrevException

log = logging.getLogger(__name__)


class LRPixelsDB:
    """
    manage Lightroom RootPixels.db database

    quality can be ["standard", "smallrender", "final", "thumbnail", "bigThumbnail", "full"]
    """

    def __init__(self, rootpix_file, open_options="mode=ro"):
        self.conn = self.cursor = None
        # self.write_perm == 'mode=rw'

        def open_db(uri):
            try:
                self.conn = sqlite3.connect(uri, uri="?" in uri)
                self.cursor = self.conn.cursor()
                return True
            except sqlite3.OperationalError:
                self.conn.close()
                return False

        self.rootpix_file = rootpix_file
        self.root_prev, _ = os.path.split(self.rootpix_file)
        if not os.path.exists(self.rootpix_file):
            raise LRPrevException(
                f"Lightroom root-pixels.db doesn't exist ({self.rootpix_file})"
            )
        modes = f"?{open_options if open_options else ''}"
        if not open_db(f"file:{self.rootpix_file}{modes}"):
            raise LRPrevException(
                f"Unable to open Lightroom root-pixels ({self.rootpix_file}"
            )

    def get_datas(self, uuid, quality=""):
        """
        return jpeg datas from uuid (uuidfile = AgLibraryFile.id_global)

        - uuid can appears several times with, different digest (Adobe_imageDevelopSettings.digest), in various quality
            (select uuid, count(uuid) as num from rootpixels group by uuid having num>1)
            schema is unique(uuid, digest)
        - quality can be ["standard", "smallrender", "final", "thumbnail", "bigThumbnail", "full"]
            (SQL:  select distinct quality from rootpixels)
        - for uuid with several entries, the length of jpegdata aren't so different
        - on my catalogs, the jpegdata size are between 700 to 8500 bytes (SQL: select min(length(jpegdata)), max(length(jpegdata)) from rootpixels )
        """
        if not self.cursor:
            log.info("not opened")
            return []
        rows = self.cursor.execute(
            "SELECT jpegData, colorProfile, croppedWidth, croppedHeight, quality FROM RootPixels WHERE uuid=?",
            (uuid,),
        ).fetchall()
        if not rows:
            raise LRPrevException("no data")
        return rows

    def insert_datas(
        self,
        uuid,
        digest,
        jpeg_datas,
        color_profile,
        cropped_width,
        cropped_height,
        quality,
    ):
        """
        insert new datas for an uuid
        """
        try:
            self.cursor.execute(
                "INSERT INTO RootPixels (uuid, digest, jpegData, colorProfile, croppedWidth, croppedHeight, quality)"
                " VALUES (?,?,?,?,?,?,?)"
                " ON CONFLICT (uuid, digest) DO UPDATE SET "
                "jpegData=excluded.JpegData, "
                "colorProfile=excluded.colorProfile,"
                "croppedWidth=excluded.croppedWidth,"
                "croppedHeight=excluded.croppedHeight,"
                "quality=excluded.quality",
                (
                    uuid,
                    digest,
                    jpeg_datas,
                    color_profile,
                    cropped_width,
                    cropped_height,
                    quality,
                ),
            )
            self.conn.commit()
        except sqlite3.Error as e:
            log.error("Error inserting data: %s", e)
            raise LRPrevException(f"Error inserting data: {e}") from e

    def close(self):
        """close database"""
        if not self.conn:
            return
        self.conn.close()
        self.conn = self.cursor = None
        log.debug("close LRPixelsDB")

    @classmethod
    def create(cls, dbpath, open_options="mode=rw"):
        """create database and return class instance"""
        directories, _ = os.path.split(dbpath)
        try:
            os.mkdir(directories)
        except FileExistsError:
            pass
        conn = sqlite3.connect(dbpath)
        cursor = conn.cursor()
        with open(
            os.path.join(
                os.path.realpath(os.path.dirname(__file__)), "./schemas/root-pixels.sql"
            ),
            encoding="utf8",
        ) as f:
            sql = f.read()
        cursor.executescript(sql)
        conn.commit()
        conn.close()
        return cls(dbpath, open_options)
