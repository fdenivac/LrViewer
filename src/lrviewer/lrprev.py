# -*- encoding: utf-8 -*-
# pylint: disable=line-too-long

"""
Access to preview image of Lightroom catalog

class LRPreviewsDB :
    Manage "previews.db" Lightroom database
    Thumbnails are stored as external files, decoded via LRPrevFile.
    Note: image orientation is orientation of camera output

class LRPrevFile :
    Read Lightroom preview files (.lrprev)

class LRPrevFileWriter:
    Build and write Lightroom preview files (.lrprev)

class LRPrevException(Exception):
    Generic Exception for module


Credits :
    parts from project https://github.com/arnar/lightroommate


HACKING files in "<CATALOG> Previews.lrdatas/":
==========
* 3 file types :
    - lrprev : photo preview
    - lrmprev : motion preview
    - lrfprev : face preview

* Structure lrprev
  ---------
    pyramid keys:
        "colorProfile":     ["AdobeRGB", "sRGB", ...], from ?
        "croppedHeight":    from Adobe_imageDevelopSettings.croppedHeight
        "croppedWidth":     from Adobe_imageDevelopSettings.croppedWidth
        "digest":           from Adobe_imageDevelopSettings.digest
        "fileTimeStamp":    optional, from table ?
        "formatVersion":    from table ?, always = 3
        "fromProxy":        optional, from table ?
        "levels":           thumbnail height, width
        "quality":          in ['standard', 'bigThumbnail', 'final', 'thumbnail', 'smallRender', 'full'], from table ?
        "uuid":             from AgLibraryFile.id_global
        "fingerprint":      optional, from table ?

    filename 'uuid-digest'
        - uuid (idem to previews.db from Adobe_Images.id_local) -> AgLibraryFile.id_global
        - digest -> Adobe_imageDevelopSettings.digest

    Structure datas
        - ALWAYS header_length ALWAYS = 32
        - ALWAYS version=0 and kind=0 for section header
        - ALWAYS version=1 and kind=0 for another sections
        - padding: bytes number after binary current section
        - images size are dimenions detected by PIL


    Study of file E:/Lightroom/La Totale/La Totale Previews.lrdata/0/0000/000038A3-9948-43E7-AEBC-6841AFE9F822-c0920be3fd1006936f49a043bacccaaf.lrprev
    --SELECT  fi.baseName || "." || fi.extension AS name, i.* FROM Adobe_images i LEFT JOIN AgLibraryFile fi ON i.rootFile = fi.id_local WHERE fi.id_global = "000038A3-9948-43E7-AEBC-6841AFE9F822"
        => id_local = 4588193
    --SELECT * from  Adobe_imageDevelopSettings WHERE digest LIKE "c0920be3fd1006936f49a043bacccaaf"
        => image = 4588193
    --SELECT * FROM Adobe_libraryImageDevelopHistoryStep WHERE digest LIKE "c0920be3fd1006936f49a043bacccaaf"
        => 4 results with image = 4588193

    Levels are "sequentials" : start from "levels_1" to "level_N" without hole
        /cygdrive/d/Devs/LrViewer> python src/lrviewer/lrprev.py | sort |uniq -c
            1 ['header', 'level_1', 'level_2', 'level_3', 'level_4', 'level_5', 'level_6', 'level_7', 'level_8', 'level_9']
            1 ['header', 'level_1', 'level_2', 'level_3', 'level_4', 'level_5', 'level_6', 'level_7', 'level_8']
           36 ['header', 'level_1', 'level_2', 'level_3', 'level_4', 'level_5', 'level_6', 'level_7']
        78838 ['header', 'level_1', 'level_2', 'level_3', 'level_4', 'level_5', 'level_6']
         7130 ['header', 'level_1', 'level_2', 'level_3', 'level_4', 'level_5']
         2340 ['header', 'level_1', 'level_2', 'level_3', 'level_4']
         4425 ['header', 'level_1', 'level_2', 'level_3']
         9562 ['header', 'level_1', 'level_2']
          117 ['header', 'level_1']
        => 102450 files (on 148677 photos)
    - max sizes (=max(width, height)) by level : see graph in stats_lprev_sizes_count.ods
        most current values :
            level_1 : 60
            level_2 : 120
            level_3 : 240
            level_4 : 480
            level_5 : 960
            level_6 : 1920

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

    def __init__(self, path, mode="rb"):
        self._file = open(path, mode)
        self._sections = []
        self._section_idxs = {}
        self._level_sizes = []
        self.pyramid = {}
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
            version, kind, length, padding = struct.unpack(">BBQQ", header[:18])
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
        self.pyramid = SLPP().decode(self.load("header").decode()[10:])
        self._level_sizes = [
            (level["width"], level["height"]) for level in self.pyramid["levels"]
        ]


class LRPrevWriterException(Exception):
    """LRPrevWriterException generic Exception"""


class LRPrevFileWriter:
    """
    Lightroom preview files (.lrprev) writer
    """

    def __init__(self, **infos):
        # jpeg data sections
        self.data_sections: list[tuple[int, int, int, bytes]] = []
        # values for pyramid
        self.color_profile = "sRGB"
        self.cropped_height = 0  # Adobe_imageDevelopSettings.croppedHeight
        self.cropped_width = 0  # Adobe_imageDevelopSettings.croppedWidth
        self.digest = ""  # Adobe_imageDevelopSettings.digest
        self.file_timestamp = None  # AgLibraryFile.modTime (rounded)
        self.finger_print = None
        self.format_version = 3
        self.from_proxy = None
        self.quality = "standard"
        self.uuid = ""  # AgLibraryFile.id_global
        # set pyramid infos
        self.set_pyramid_infos(**infos)

    def set_pyramid_infos(self, **infos):
        """
        set pyramid infos
        """
        for key, value in infos.items():
            if key not in [
                "color_profile",
                "cropped_height",
                "cropped_width",
                "digest",
                "file_timestamp",
                "finger_print",
                "format_version",
                "quality",
                "uuid",
            ]:
                raise LRPrevWriterException(f"key unsupported : {key}")
            setattr(self, key, value)

    def add_thumb(self, width: int, height: int, data: bytes):
        """
        add thumbnail

        max_size : max(width, height)
        width, height : jpeg dimensions
        datas : jpeg datas
        """
        self.data_sections.append((max(width, height), width, height, data))

    def write(self, fname):
        """write lrprev file"""
        with open(fname, "wb") as file:
            # sort thumbnails by size (first item of tuple)
            self.data_sections.sort(key=lambda item: item[0])
            # build pyramid and write section header
            self._write_section(file, "header", self._build_pyramid())
            for level, (_, _, _, datas) in enumerate(self.data_sections):
                section_level = f"level_{level + 1}"
                self._write_section(file, section_level, datas)

    def standard_pathname(self):
        """return standard path name in '..Previews.lrdata' directory"""
        assert self.uuid != 0 and self.digest != 0
        return os.path.join(
            self.uuid[0], self.uuid[0:4], f"{self.uuid}-{self.digest}.lrprev"
        )

    def _build_pyramid(self):
        """
        build data header : lua pyramid

        data_sections must be sorted before
        """
        lua = {}
        lua["colorProfile"] = self.color_profile if self.color_profile else "AdobeRGB"
        lua["croppedHeight"] = self.cropped_height
        lua["croppedWidth"] = self.cropped_width
        lua["digest"] = self.digest
        if self.file_timestamp is not None:
            lua["fileTimeStamp"] = self.file_timestamp
        if self.finger_print is not None:
            lua["fingerprint"] = self.finger_print
        lua["formatVersion"] = self.format_version
        if self.from_proxy is not None:
            lua["fromProxy"] = self.from_proxy

        lua["levels"] = []
        for _, width, height, _ in self.data_sections:
            lua["levels"].append({"height": height, "width": width})

        lua["quality"] = self.quality
        lua["uuid"] = self.uuid

        lua = f"pyramid = {SLPP().encode(lua)}\n"
        return bytes(lua, encoding="ascii")

    def _write_section(self, file: any, name: str, datas: bytes):
        """write section, padding from current file position"""
        assert file.tell() & 0x0F == 0
        version = 0 if name == "header" else 1
        padding = 16 - (len(datas) & 0x0F) if len(datas) & 0x0F else 0
        # write header
        header = struct.pack(
            ">4sHBBQQ8s",
            b"AgHg",
            32,
            version,
            0,
            len(datas),
            padding,
            bytes(name, encoding="ascii"),
        )
        file.write(header)
        # write data
        file.write(datas)
        # write padding
        if padding != 0:
            file.write(padding * b"\0")

    def from_file(self, fname):
        """init datas from existant lrprev file"""
        if not os.path.exists(fname):
            raise LRPrevException(f"File not found: {fname}")
        lrprev = LRPrevFile(fname)
        self.color_profile = lrprev.pyramid["colorProfile"]
        self.cropped_height = lrprev.pyramid["croppedHeight"]
        self.cropped_width = lrprev.pyramid["croppedWidth"]
        self.digest = lrprev.pyramid["digest"]
        self.file_timestamp = lrprev.pyramid["fileTimeStamp"]
        if "fingerprint" in lrprev.pyramid:
            self.finger_print = lrprev.pyramid["fingerprint"]
        self.format_version = lrprev.pyramid["formatVersion"]
        self.from_proxy = lrprev.pyramid["fromProxy"]
        self.quality = lrprev.pyramid["quality"]
        self.uuid = lrprev.pyramid["uuid"]
        #  load jpeg datas
        for section_name in lrprev.sections:
            if section_name == "header":
                continue
            datas = lrprev.load(section_name)
            _, level = section_name.split("_")
            width = lrprev.pyramid["levels"][int(level) - 1]["width"]
            height = lrprev.pyramid["levels"][int(level) - 1]["height"]
            self.add_thumb(width, height, datas)


class LRPreviewsDB:
    """
    manage Lightroom previews.db database

    Use only the ImageCacheEntry table
    - lrprev filename built from cache can be not existant
    - lrprev file can exists, but infos missing in table
    """

    def __init__(self, prevdb_file, open_options="mode=ro"):
        self.conn = self.cursor = None

        def open_db(uri):
            try:
                self.conn = sqlite3.connect(uri, uri="?" in uri, timeout=10)
                self.cursor = self.conn.cursor()
                return True
            except sqlite3.OperationalError:
                self.conn.close()
                return False

        self.prevdb_file = prevdb_file
        self.root_prev, _ = os.path.split(self.prevdb_file)
        if not os.path.exists(self.prevdb_file):
            raise LRPrevException(
                f'Lightroom previews.db doesn\'t exist "{self.prevdb_file}")'
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
            raise LRPrevException("no path")
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

    def insert_datas(self, lrid, uuid, digest, orientation):
        """
        insert new datas in database
        """
        try:
            self.cursor.execute(
                "INSERT INTO ImageCacheEntry (imageId, uuid, digest, orientation) VALUES (?,?,?,?)",
                (lrid, uuid, digest, orientation),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
            log.error("Failed to insert data in LRPreviewsDB")

    def close(self):
        """close database"""
        if not self.conn:
            return
        self.conn.close()
        self.conn = self.cursor = None
        log.debug("close LRPreviewsDB")

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
                os.path.realpath(os.path.dirname(__file__)), "./schemas/previews.sql"
            ),
            encoding="utf8",
        ) as f:
            sql = f.read()
        cursor.executescript(sql)
        conn.commit()
        conn.close()
        return cls(dbpath, open_options)
