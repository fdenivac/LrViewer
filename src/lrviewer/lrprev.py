# -*- encoding: utf-8 -*-
# pylint: disable=line-too-long

"""
Access to preview image of Lightroom catalog

class LRPixelsDB :
    Manage "root-pixels.db" Lightroom database
    Thumbnails are stored in database

class LRPreviewsDB :
    Manage "previews.db" Lightroom database
    Thumbnails are stored as external files, decoded via LRPrevFile

class LRPrevFile :
    Read Lightroom preview files (.lrprev)

class LRPrevException(Exception):
    Generic Exception for module


Credits :
    parts from project https://github.com/arnar/lightroommate
"""

import os
import struct
import sqlite3
import logging

from lrtools.slpp import SLPP

log = logging.getLogger(__name__)


class LRPrevException(Exception):
    """LRPrevException generic Exception"""


class LRPrevFile:
    """
    datas access to Lightroom preview files (.lrprev)
    """

    def __init__(self, path):
        self._file = open(path, "rb")
        self._sections = []
        self._section_idxs = {}
        self._level_sizes = []
        self._parse_headers()

    @property
    def sections(self):
        """return section names list"""
        return [s["name"] for s in self._sections]

    def load(self, section_name):
        """return specific section"""
        idx = self._section_idxs[section_name]
        hdr = self._sections[idx]
        self._file.seek(hdr["offset"])
        data = self._file.read(hdr["length"])
        return data

    def level_sizes(self, section_name=None):
        """return sizes for section_name or all levels sizes"""
        if section_name:
            _, level = section_name.split("_")
            return self._level_sizes[int(level) - 1]
        return self._level_sizes

    def section_info(self, section_name):
        """return section datas"""
        return self._sections[self._section_idxs[section_name]]

    def close(self):
        """close preview file"""
        self._file.close()

    def _parse_headers(self):
        """parse header and lua pyramid"""
        self._file.seek(0)
        i = 0
        while self._file.read(4) == b"AgHg":
            (header_length,) = struct.unpack(">H", self._file.read(2))
            header = self._file.read(header_length - 6)
            (version, kind, length, padding) = struct.unpack(">BBQQ", header[:18])
            name = header[18:].split(b"\0")[0].decode()
            self._sections.append(
                {
                    "name": name,
                    "length": length,
                    "version": version,
                    "kind": kind,
                    "offset": self._file.tell(),
                }
            )
            self._section_idxs[name] = i
            i += 1
            self._file.seek(length + padding, os.SEEK_CUR)
        # parse lua pyramid
        datas = self.load("header").decode()[10:]
        header = SLPP().decode(datas)
        self._level_sizes = [
            (level["width"], level["height"]) for level in header["levels"]
        ]


class LRPreviewsDB:
    """
    manage Lightroom previews.db database
    """

    def __init__(self, prevdb_file, open_options="mode=ro"):
        self.conn = self.cursor = None

        def open_db(uri):
            try:
                self.conn = sqlite3.connect(uri, uri="?" in uri)
                self.cursor = self.conn.cursor()
                return True
            except sqlite3.OperationalError:
                self.conn.close()
                return False

        self.prevdb_file = prevdb_file
        self.root_prev, _ = os.path.split(self.prevdb_file)
        if not os.path.exists(self.prevdb_file):
            raise LRPrevException(
                f'Lightroom previews.bd doesn\'t exist "{self.prevdb_file}")'
            )
        modes = f"?{open_options if open_options else ''}"
        if not open_db(f"file:{self.prevdb_file}{modes}"):
            raise LRPrevException(
                f'Unable to open Lightroom preview.db ("{self.prevdb_file}")'
            )

    def get_prev_infos(self, lr_id):
        """Get preview infos from lightroom id_local
        Returns:
            - preview filename or empty string if not exists
            - image orientation
        """
        rows = self.cursor.execute(
            "SELECT uuid, digest,orientation FROM ImageCacheEntry WHERE imageId=?",
            (lr_id,),
        ).fetchone()
        if not rows:
            raise LRPrevException("no data")
        uuid, digest, orientation = rows
        fname_prev = f"{self.root_prev}/{uuid[:1]}/{uuid[:4]}/{uuid}-{digest}.lrprev"
        if not os.path.exists(fname_prev):
            raise LRPrevException
        return (fname_prev, orientation)

    def get_uuid_orient(self, lr_id):
        """Get uuid and orientation from lightroom id_local"""
        row = self.cursor.execute(
            "SELECT uuid, orientation FROM ImageCacheEntry WHERE imageId=?", (lr_id,)
        ).fetchone()
        if not row:
            raise LRPrevException
        uuid, orientation = row
        return uuid, orientation

    def close(self):
        """close database"""
        if not self.conn:
            return
        self.conn.close()
        self.conn = self.cursor = None
        log.info("closed")


class LRPixelsDB:
    """
    manage Lightroom RootPixels.db database

    quality can be ["standard", "smallrender", "final", "thumbnail", "bigThumbnail", "full"]
    """

    def __init__(self, rootpix_file, open_options="mode=ro"):
        self.conn = self.cursor = None

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
        return jpeg datas

        - uuid can appears several times with same or different quality
        - quality can be ["standard", "smallrender", "final", "thumbnail", "bigThumbnail", "full"]
            (SQL:  select distinct quality from rootpixels)
        - an uuid can appear several times (SQL: select uuid, count(uuid) as num from rootpixels group by uuid having num>1)
        - for uuid with several entries, the lenght of jpegdata aren't so different
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
            raise LRPrevException
        return rows

    def close(self):
        """close database"""
        if not self.conn:
            return
        self.conn.close()
        self.conn = self.cursor = None
        log.info("closed")
