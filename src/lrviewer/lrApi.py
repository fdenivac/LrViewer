# -*- encoding: utf-8 -*-
# pylint: disable=line-too-long,invalid-name

"""
Encapsulate Lightroom SQL Tools API (lrtools)

"""

import traceback
import logging
import sqlite3


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

    def __init__(self, lrconfig: LRToolConfig):
        self.lrconfig = lrconfig
        self.api = None
        self._lrcat_file = ""
        self.exception = ""
        self.connected = False
        self.default_columns = "name,datecapt,aperture,speed,iso"

        self._columns = []
        self._hidden_columns = []
        self._hidden_columns_name = []
        self._map_indexes = {}  # map internal index to user index

        self._dcriteria = {}
        self.query_results = []
        self.column_specs = []
        self.user_sortcol = "1"
        self.current_id_smart = None

    def open(self, lrcat_file: str) -> bool:
        """open Lightroom catalog"""
        try:
            self._lrcat_file = lrcat_file
            self.api = LRCatDB(self.lrconfig, self._lrcat_file)
            self.connected = True
            self.query_results = []
            return True
        except LRCatException as e:
            self.exception = str(e)
            self.connected = False
            self.query_results = []
            return False

    def is_connected(self) -> bool:
        """status connected"""
        return self.connected

    def catalog_path(self) -> str:
        """return current Lightroom catalog"""
        return self._lrcat_file

    def set_columns(self, columns: str) -> None:
        """default columns when query() not using columns"""
        self.default_columns = columns
        self._set_columns(self.default_columns)

    def add_hidden_columns(self, columns: str) -> None:
        """add hidden columns"""
        columns = [col.strip().lower() for col in columns.split(",")]
        for col_name in columns:
            if not col_name in self._hidden_columns_name:
                self._hidden_columns_name.append(col_name)

    def remove_hidden_columns(self, columns: str) -> None:
        """remove hidden columns"""
        columns = [col.strip().lower() for col in columns.split(",")]
        for col_name in columns:
            if col_name in self._hidden_columns_name:
                self._hidden_columns_name.remove(col_name)

    def _set_columns(self, columns: str) -> None:
        """internal set columns"""
        self._columns = [col.strip().lower() for col in columns.split(",")]
        self._hidden_columns = [False] * len(self._columns)
        # "id" column no needed when criter "distinct", or columns "count()", "countby()""
        need_id = "distinct" not in self._dcriteria
        if need_id:
            for col in self._columns:
                if col.startswith("count(") or col.startswith("countby("):
                    need_id = False
                    break
        if need_id:
            self.add_hidden_columns("id")

        # add hidden columns to query
        for col in self._hidden_columns_name:
            if col in self._columns:
                # column exists, do not change visibility
                continue
            self._columns.append(col)
            self._hidden_columns.append(True)

        self._build_map_indexes()

    def _can_reuse_columns(self) -> bool:
        """return True if current columns is reusable by query"""
        if len(self._columns) == 0:
            return False
        # check for count() or countby
        for col in self._columns:
            if col.startswith("count(") or col.startswith("countby("):
                return False
        return True

    def prepare_query(self, criteria: str = None, columns=None) -> None:
        """set column, criteria"""
        self.current_id_smart = None
        if criteria is not None:
            # set dict criteria before work on columns
            self._dcriteria = criteria_to_dict(criteria)
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

        if criteria is not None:
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
        log.info("query started : %s %s", columns, criteria)
        try:
            self.prepare_query(criteria, columns)
        except LRSelectException as _e:
            self.exception = str(_e)
            self._clean_on_error()
            log.error("query failed : %s", self.exception)
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
        ) as e:
            self.exception = str(e)
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

    def query_sort(self, column: int, ascending_order: bool) -> int:
        """set sort column and execute query already set"""
        assert "sort" in self._dcriteria
        if isinstance(column, str):
            if ascending_order:
                column = f"-{column}"
            self._dcriteria["sort"] = [column]
            self.user_sortcol = column
        else:
            assert isinstance(column, int)
            column = self._index_internal(column)
            if ascending_order:
                self._dcriteria["sort"] = [-column if ascending_order else column]
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
        except (LRSelectException, SmartException, sqlite3.OperationalError) as e:
            self.exception = str(e)
        return self._finalize_query()

    def query_smart_data(self, smart_data: str) -> int:
        """query using lr smart data (lua)"""
        self.query_results = []
        builder = SQLSmartColl(self.lrconfig, self.api, smart_data)
        sql = builder.build_sql(",".join(self._columns))
        log.debug("sql by smartdata: %s", sql)
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
            log.error("query failed : %s", self.exception)
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

    def columns(self, visible_col: bool = False) -> str:
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

    def _index_internal(self, index: int) -> int:
        """return internal index from visible index"""
        try:
            return self._map_indexes[index]
        except KeyError:
            log.error("BUG KeyError map_indexes[%s]", index)
            return -1

    def _index_from_internal(self, index: int) -> int:
        """return visible index from internal index"""
        # TODO try for track rare bug
        try:
            rmap = {v: k for k, v in self._map_indexes.items()}
            return rmap[index]
        except KeyError:
            log.error(f"BUG _index_from_internal index:{index}, rmap:{rmap}")
            return 0

    def query_result(
        self, row: int, column: int, visible_col: bool = True, raw: bool = False
    ):
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
            return func_format(value)
        return value

    def column_index(self, name: str) -> int:
        """return column index or -1 if no name in columns"""
        if name not in self._columns:
            return -1
        return self._columns.index(name)

    def has_id_column(self) -> bool:
        """True if "id" column present"""
        return self.column_index("id") != -1

    def columns_count(self, visible_col: bool = False) -> int:
        """current columns"""
        if visible_col:
            return len(self._map_indexes)

        return len(self._columns)

    def column(self, index: int, visible_col: bool) -> str:
        """return column name for index"""
        if visible_col:
            index_int = self._index_internal(index)
            return self._columns[index_int]

        return self._columns[index]

    def query_count(self) -> int:
        """return query count"""
        return len(self.query_results)

    def format_data(self, column: int, data: str, visible_col: bool = False) -> str:
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
lr_api = PhotosAPI(LRToolConfig())
