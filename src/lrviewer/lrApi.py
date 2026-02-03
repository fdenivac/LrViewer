# -*- encoding: utf-8 -*-
# pylint: disable=line-too-long,invalid-name

"""
Encapsulate Lightroom SQL Tools API (lrtools)

"""

import traceback
import os
import logging
import sqlite3

from xml.parsers.expat import ExpatError
import xmltodict

from lrtools.lrcat import (
    LRCatDB,
    LRCatException,
)
from lrtools.lrselectgeneric import LRSelectException
from lrtools.display import prepare_display_columns, DEFAULT_SPEC
from lrtools.lrsmartcoll import SQLSmartColl, select_smart, SmartException
from lrtools.lrselectphoto import (
    criteria_to_dict,
    dict_to_criteria,
)
from lrtools.lrtoolconfig import LRToolConfig


log = logging.getLogger(__name__)


class PhotosAPI:
    """encapsulates lrtools api"""

    def __init__(self):
        self.lrconfig = LRToolConfig()
        self.api = None
        self.lrcat_file = ""
        self.exception = ""
        self.connected = False
        self.default_columns = "name,datecapt,aperture,speed,iso"

        self._columns = []
        self._hidden_columns = []
        self._map_indexes = {}  # map internal index to user index

        self._dcriteria = {}
        self.query_results = []
        self.column_specs = []
        self.user_sortcol = "1"
        self.current_id_smart = None

    def open(self, lrcat_file):
        """open Lightroomm catalog"""
        # open Lightroom catalog
        try:
            self.lrcat_file = lrcat_file
            self.api = LRCatDB(self.lrconfig, lrcat_file)
            self.connected = True
            self.query_results = []
            return True
        except LRCatException as _e:
            self.exception = str(_e)
            self.connected = False
            self.query_results = []
            return False

    def is_connected(self) -> bool:
        """status connected"""
        return self.connected

    def set_columns(self, columns) -> None:
        """default columns when query() not using columns"""
        self.default_columns = columns
        self._set_columns(self.default_columns)

    def _set_columns(self, columns) -> None:
        """internal set columns"""
        self._columns = [col.strip().lower() for col in columns.split(",")]
        # "id" column no needed when criter "distinct", or columns "count()", "countby()""
        need_id = "distinct" not in self._dcriteria
        if need_id:
            for col in self._columns:
                if col.startswith("count(") or col.startswith("countby("):
                    need_id = False
                    break
        # manage hidden "id" column
        hidden_id = False
        if need_id:
            hidden_id = "id" not in self._columns
            if hidden_id:
                self._columns.insert(0, "id")
        self._hidden_columns = [False] * len(self._columns)
        # final
        if hidden_id:
            self._hidden_columns[self.column_index("id")] = True
        self._build_map_indexes()

    def _can_reuse_columns(self):
        """return True if current columns is reusable by query"""
        if len(self._columns) == 0:
            return False
        # check for count() or countby
        for col in self._columns:
            if col.startswith("count(") or col.startswith("countby("):
                return False
        return True

    def prepare_query(self, criteria=None, columns=None) -> None:
        """set column, criteria"""
        self.current_id_smart = None
        if criteria:
            # set dict criteria before work on columns
            self._dcriteria = criteria_to_dict(criteria)
            # TODO A VERIFIER
            # if not columns:
            if "sort" not in self._dcriteria:
                # previous columns not modified : reuse previous sort TODO BUT SAFE ?
                self._dcriteria["sort"] = [self.user_sortcol]
        else:
            # check set minimun : default sort
            if not self._dcriteria or "sort" not in self._dcriteria:
                self._dcriteria["sort"] = "1"

        if columns:
            self._set_columns(columns)
        else:
            # the Lightroom collections doesn't have columns
            # reuse current columns (already set by previous query or by explicit prepare_query(columns))
            # or use default columns
            if not self._can_reuse_columns():
                self._set_columns(self.default_columns)

        if criteria:
            if "sort" in self._dcriteria:
                user_sortcol = self._dcriteria["sort"][0]
                self.user_sortcol = user_sortcol

                assert isinstance(user_sortcol, str)

                if user_sortcol.startswith("-") and user_sortcol[1:].isdecimal():
                    user_sortcol = self._index_internal(int(user_sortcol[1:]) - 1)
                    if user_sortcol < 0:
                        raise LRSelectException(
                            "sort invalid (must be >=1 and <= column number"
                        )
                    user_sortcol = -(user_sortcol + 1)

                elif user_sortcol.isdecimal():
                    user_sortcol = self._index_internal(int(user_sortcol) - 1)
                    if user_sortcol < 0:
                        raise LRSelectException(
                            "sort invalid (must be >=1 and <= column number"
                        )
                    user_sortcol = user_sortcol + 1

                self._dcriteria["sort"] = [user_sortcol]

            else:
                # some lrtools column have a parameter (ex: "name=full")
                keyval = self.column(0, visible_col=True)
                name = keyval.split("=")[0]
                self._dcriteria["sort"] = [name]
                self.user_sortcol = keyval

    def query(self, criteria=None, columns=None) -> bool:
        """
        query from criteria and columns.
        Return True if success
        """
        try:
            self.prepare_query(criteria, columns)
        except LRSelectException as _e:
            self.exception = str(_e)
            self._clean_on_error()
            log.info("query failed : %s", self.exception)
            return False
        return self._query()

    def _query(self) -> bool:
        """
        (internal) query with current columns, criteria.
        Return True if success
        """
        self.query_results = []
        if not self.connected:
            return False
        try:
            self.query_results = self.api.lrphoto.select_generic(
                ",".join(self._columns), dict_to_criteria(self._dcriteria)
            ).fetchall()
            self.exception = ""
        except (
            LRSelectException,
            sqlite3.OperationalError,
            sqlite3.DatabaseError,
        ) as _e:
            self.exception = str(_e)
        return self._finalize_query()

    def sort_column(self) -> int:
        """
        return sort current sort column (sql ORDER value)
        """
        return self.user_sortcol

    def sort_column_index(self) -> int:
        """
        return sort column visible ("id" hidden) index (one based)
        """
        if self.user_sortcol.startswith("-") and self.user_sortcol[1:].isnumeric():
            user_sortcol = int(self.user_sortcol[1:]) - 1
            return -user_sortcol

        if self.user_sortcol.isnumeric():
            user_sortcol = int(self.user_sortcol) - 1
            return user_sortcol

        if self.user_sortcol.startswith("-"):
            index = self.column_index(self.user_sortcol[1:])
            index = self._index_from_internal(index)
            return -index
        index = self.column_index(self.user_sortcol)
        index = self._index_from_internal(index)
        return index

    def query_sort(self, column: any, ascendingOrder: bool) -> int:
        """set sort column and execute query already set"""
        assert "sort" in self._dcriteria
        if isinstance(column, str):
            if ascendingOrder:
                column = f"-{column}"
            self._dcriteria["sort"] = [column]
            self.user_sortcol = column
        else:
            assert isinstance(column, int)
            column = self._index_internal(column)
            if ascendingOrder:
                self._dcriteria["sort"] = [-column if ascendingOrder else column]
        log.info("set sort=%s", self._dcriteria["sort"][0])
        if self.current_id_smart is not None:
            return self.smart_query(self.current_id_smart, self._dcriteria["sort"][0])
        return self._query()

    def smart_query(self, id_smart: int, sort_column: str) -> int:
        """Try to execute smart collection"""
        self.query_results = []
        try:
            self.current_id_smart = id_smart
            self.query_results = select_smart(
                self.lrconfig, self.api, id_smart, ",".join(self._columns), sort_column
            )
            self.exception = ""
        except (LRSelectException, SmartException, sqlite3.OperationalError) as _e:
            self.exception = str(_e)
        return self._finalize_query()

    def query_smart_data(self, smart_data: str) -> int:
        """query using lr smart data (lua)"""
        self.query_results = []
        builder = SQLSmartColl(self.lrconfig, self.api, smart_data)
        sql = builder.build_sql(",".join(self._columns))
        log.info("sql by smartdata: %s", sql)
        try:
            self.query_results = self.api.cursor.execute(sql).fetchall()
        except (LRSelectException, sqlite3.OperationalError) as _e:
            self.exception = str(_e)
        return self._finalize_query()

    def _clean_on_error(self):
        """clean on error"""
        self.query_results = []

    def _finalize_query(self) -> bool:
        """finalize, clean after query"""
        if self.exception:
            log.info("query failed : %s", self.exception)
            self._clean_on_error()
            return False
        if self.query_results:
            self.column_specs = prepare_display_columns(self._columns, [])
            # basic check : detect if suffisant column
            for i in range(len(self.query_results[0])):
                if i < len(self.column_specs):
                    continue
                self.column_specs[i] = (f"column{i}", DEFAULT_SPEC[0], DEFAULT_SPEC[1])
        log.info("query return %s results", len(self.query_results))
        return len(self.query_results) > 0

    def criteria(self) -> str:
        """return current criteria for user (manage "id" hidden)"""
        assert "sort" in self._dcriteria
        dcriteria = self._dcriteria.copy()
        dcriteria["sort"] = [self.user_sortcol]
        return dict_to_criteria(dcriteria)

    def columns(self, visible_col=False) -> str:
        """return current columns in string format"""
        if visible_col:
            columns = [
                col
                for id, col in enumerate(self._columns)
                if not self._hidden_columns[id]
            ]
            return ",".join(columns)
        return ",".join(self._columns)

    def hide_column(self, index: int, hide: bool):
        """hide column at index (not used by lrview)

        To be tested (view and model must be reseted)
        """
        if index >= self.columns_count():
            raise LRSelectException(f"hide({hide})_column({index}) invalid")
        self._hidden_columns[index] = hide
        # update map visible columns index to internal
        self._build_map_indexes()

    def _build_map_indexes(self):
        """(internal) build map indexes"""
        self._map_indexes = {}
        index_ext = 0
        for index_int in range(0, self.columns_count()):
            if self._hidden_columns[index_int]:
                continue
            self._map_indexes[index_ext] = index_int
            index_ext += 1

    def _index_internal(self, index) -> dict:
        """return internal index from visible index"""
        try:
            return self._map_indexes[index]
        except KeyError:
            log.error("BUG KeyError map_indexes[%s]", index)
            return -1

    def _index_from_internal(self, index):
        """return visible index from internal index"""
        # TODO try for track rare bug
        try:
            rmap = {v: k for k, v in self._map_indexes.items()}
            return rmap[index]
        except KeyError:
            print(f"BUG _index_from_internal index:{index}, rmap:{rmap}")
            traceback.print_stack()
            return 0

    def query_result(self, row: int, column: int, visible_col=True, raw=False):
        """return query result from row and visible column"""
        if visible_col:
            column = self._index_internal(column)
        _, _, func_format = self.column_specs[column]
        if raw:
            return self.query_results[row][column]
        value = self.query_results[row][column]
        if func_format:
            if value is None:
                return value
            return func_format(self.query_results[row][column])
        return self.query_results[row][column]

    def column_index(self, name: str):
        """return column index or -1 if no name in columns"""
        if name not in self._columns:
            return -1
        return self._columns.index(name)

    def has_id_column(self) -> bool:
        """True if "id" column present"""
        return self.column_index("id") != -1

    def columns_count(self, visible_col=False) -> int:
        """current columns"""
        if visible_col:
            return len(self._map_indexes)

        return len(self._columns)

    def column(self, index: int, visible_col) -> str:
        """return column name for index"""
        if visible_col:
            index_int = self._index_internal(index)
            return self._columns[index_int]

        return self._columns[index]

    def query_count(self) -> int:
        """return query count"""
        return len(self.query_results)

    def format_data(self, column: int, data: str, visible_col=False) -> str:
        """format specific datas"""
        if visible_col:
            column = self._index_internal(column)
        _, _, func_format = self.column_specs[column]
        if data is None:
            data = ""
        elif func_format:
            data = func_format(data)
        return data

    def get_lr_id(self, row: int) -> int:
        """return lightroom photo index at row"""
        col = self.column_index("id")
        if col == -1:
            log.info("no 'id' column")
            return None
        return self.query_results[row][col]


# create default PhotosAPI instance
lr_api = PhotosAPI()


class PhotoMetadatas(PhotosAPI):
    """
    retrieve / manage metadatas for unique photo
    """

    LTR_COLNAMES = {
        "name": ("Filename", "name and extension"),
        "name=full": ("Full filename",),
        "rating": (
            "Rating",
            "from 0 to 5",
        ),
        "flag": (
            "Flag",
            "flagged, unflagged, rejected",
        ),
        "datecapt": ("Date Capture",),
        "datemod": ("Date Last Modification",),
        "datehist": ("Date History",),
        "modcount": ("Count Modifications",),
        "dims": ("Dimensions",),
        "aspectratio": ("Aspect Ratio",),
        "aperture": ("Aperture",),
        "speed": ("Speed",),
        "iso": ("ISO",),
        "focal": ("Focal",),
        "flash": ("Flash",),
        "monochrome": ("Monochrome",),
        "camera": ("Camera",),
        "camerasn": ("Camera Serial Number",),
        "lens": ("Lens",),
        "keywords": ("Keywords",),
        "collections": ("Collections",),
        "title": ("Title",),
        "caption": ("Caption",),
        "creator": ("Creator",),
        "copyright": ("Copyright",),
        "location": ("Location",),
        "city": ("City",),
        "country": ("Country",),
        "state": ("State",),
        "latitude": ("Latitude",),
        "longitude": ("Longitude",),
        "colorlabel": ("Color Label",),
    }

    def __init__(self):
        super().__init__()
        self.names = (
            "name=full_vc,datecapt,datemod,caption,rating,colorlabel,flag,creator,copyright,modcount,aperture,speed,iso,focal,"
            "camera,camerasn,lens,monochrome,flash,dims,aspectratio,keywords,collections,"
            "location,city,country,state,latitude,longitude,master,stack,stackpos,xmp"
        )
        self._metadatas = {}

    def clone_connection(self, other: PhotosAPI):
        """clone connection from other PhotosAPI instance"""
        self.api = other.api
        self.connected = other.connected

    def readMetadatas(self, id_photo):
        """set metadatas"""
        self._metadatas = {}

        def add_meta(name, value):
            if value is None:
                return
            if name in self.LTR_COLNAMES:
                name = self.LTR_COLNAMES[name][0]
            self._metadatas[name] = value

        logging.disable(logging.INFO)
        self.query(f"id={id_photo}", self.names)
        logging.disable(logging.NOTSET)
        if self.exception:
            return False

        # metadatas are displayed in self.names order
        #  but some metadatas must be extracted from "xmp"

        # TODO filter and categories of metadatas (main,iptc,gps,...) to do in metadatasView

        xmp = {}
        if "xmp" in self.names:
            try:
                value = self.query_result(
                    0, self.column_index("xmp"), visible_col=False
                )
                xmp = xmltodict.parse(value)
                xmp = xmp["x:xmpmeta"]["rdf:RDF"]["rdf:Description"]
            except ExpatError as _e:
                log.error("Failed to parse xmp : %s", _e)

        for index, name in enumerate(self.names.split(",")):
            if name == "xmp":
                continue
            index = self.column_index(name)
            if index < 0:
                log.warning("metadatas- no column %s", name)
                continue
            value = self.query_result(0, index, visible_col=False)

            if name == "caption":
                # introduce xmp "title" before "caption"
                if "dc:title" in xmp:
                    li = xmp["dc:title"]["rdf:Alt"]["rdf:li"]
                    if "#text" in li:
                        self._metadatas["Title"] = li["#text"]

            if name == "keywords":
                add_meta(name, value)
                # introduce "hierarchical keywords" after "keywords"
                if "lr:hierarchicalSubject" in xmp:
                    self._metadatas["Hierarchical Keywords"] = xmp[
                        "lr:hierarchicalSubject"
                    ]["rdf:Bag"]["rdf:li"]
                continue

            if name == "aspectratio":
                # introduce "projection" after "aspectratio"
                add_meta(name, value)
                if "@GPano:ProjectionType" in xmp:
                    self._metadatas["Pano Projection"] = xmp["@GPano:ProjectionType"]
                continue

            if name == "name=full_vc":
                folder, name = os.path.split(value)
                self._metadatas["Name"] = name
                self._metadatas["Folder"] = folder
                continue

            if name == "colorlabel" and not value:
                continue

            add_meta(name, value)

        return True

    def metadatas(self) -> dict:
        """return metadatas"""
        return self._metadatas

    def gps_location(self) -> tuple[float, float]:
        """return gps location in tuple (longitude, latitude) or (None, None)"""
        try:
            return (
                self.query_results[0][self.column_index("latitude")],
                self.query_results[0][self.column_index("longitude")],
            )
        except IndexError:
            return (None, None)
