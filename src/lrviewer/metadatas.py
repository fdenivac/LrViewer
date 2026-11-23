"""
Build a set of metadatas for photos selection
"""

import os
import logging
from typing import List, Dict

from xml.parsers.expat import ExpatError
import xmltodict

from lrtools.lrtoolconfig import LRToolConfig

from lrApi import PhotosAPI

log = logging.getLogger(__name__)

MIXED_VALUES = "<mixed>"


class PhotoMetadatas(PhotosAPI):
    """
    retrieve / manage metadatas one or more photo

    differents values for a metadata are replaced by string "<mixed>"
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
        super().__init__(LRToolConfig())
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

    def read_metadatas(self, id_photos: List[str]):
        """Reads metadata for a list of photo IDs"""
        self._metadatas = {}
        if not id_photos:
            return

        names = f"id,{self.names}"

        # lrtools has not the IN syntax :
        #   workaround by replacing the WHERE equality (WHERE i.id_local = 0)" by IN id list
        self.prepare_query(columns=names, criteria="id=0")
        sql = self.api.lrphoto.select_generic(names, "id=0", sql=True)
        sql = sql.replace(
            "WHERE i.id_local = 0",
            f"WHERE i.id_local IN ({','.join(map(str,id_photos))})",
        )
        self.query_results = self.api.cursor.execute(sql).fetchall()
        self._finalize_query()

        for row_id in range(0, len(self.query_results)):
            self._metadatas_photo(row_id)

    def _metadatas_photo(
        self,
        row_index: int,
    ) -> Dict:
        """
        append metadatas of a photo to self._metadatas
        store MIXED_VALUES when metadata value for a key is different
        """

        def add_meta(name: str, value: any):
            if name in self.LTR_COLNAMES:
                name = self.LTR_COLNAMES[name][0]
            if name in self._metadatas and self._metadatas[name] != value:
                self._metadatas[name] = MIXED_VALUES
            else:
                if value is not None:
                    self._metadatas[name] = value

        # metadatas are displayed in self.names order
        #  but some metadatas must be extracted from "xmp"

        # TODO filter and categories of metadatas (main,iptc,gps,...) to do in metadatasView

        xmp = {}
        if "xmp" in self.names:
            try:
                value = self.query_result(
                    row_index, self.column_index("xmp"), visible_col=False
                )
                xmp = xmltodict.parse(value)
                xmp = xmp["x:xmpmeta"]["rdf:RDF"]["rdf:Description"]
            except ExpatError as _e:
                log.error("Failed to parse xmp : %s", _e)

        for index, name in enumerate(self.names.split(",")):
            if name in ["id", "xmp"]:
                continue
            if name in self._metadatas and self._metadatas[name] == MIXED_VALUES:
                continue
            index = self.column_index(name)
            if index < 0:
                log.warning("metadatas- no column %s", name)
                continue
            value = self.query_result(row_index, index, visible_col=False)

            if name == "caption":
                # introduce xmp "title" before "caption"
                if "dc:title" in xmp:
                    li = xmp["dc:title"]["rdf:Alt"]["rdf:li"]
                    if "#text" in li:
                        add_meta("Title", li["#text"])
                continue

            if name == "keywords":
                add_meta(name, value)
                # introduce "hierarchical keywords" after "keywords"
                if "lr:hierarchicalSubject" in xmp:
                    add_meta(
                        "Hierarchical Keywords",
                        xmp["lr:hierarchicalSubject"]["rdf:Bag"]["rdf:li"],
                    )
                continue

            if name == "aspectratio":
                # introduce "projection" after "aspectratio"
                add_meta(name, value)
                if "@GPano:ProjectionType" in xmp:
                    add_meta("Pano Projection", xmp["@GPano:ProjectionType"])
                continue

            if name == "name=full_vc":
                folder, name = os.path.split(value)
                add_meta("Name", name)
                add_meta("Folder", folder)
                continue

            if name == "colorlabel" and not value:
                continue

            add_meta(name, value)

    def metadatas(self) -> dict:
        """return metadatas"""
        return self._metadatas
