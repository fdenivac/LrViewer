# -*- encoding: utf-8 -*-
# pylint: disable=line-too-long,invalid-name

"""
Folium Map Widget

Supported map : all maps not needing specific attribute or registration
"""

# infos:
#     -  self.webView.destroyed.connect(self._on_destroy) -> signal never seen
#
#     - on init application, first set_location fails if map page is not fully loaded :
#         fix around using a differed call on signal "loadFinished"


import io
import json
import logging
import time

from branca.element import Element
from PySide6 import QtWidgets
from PySide6.QtWebEngineWidgets import (
    QWebEngineView,
)
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtGui import (
    QCursor,
    QAction,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QObject,
    QEventLoop,
    QCoreApplication,
)
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
)
from jinja2 import Template
import folium
from folium.map import FeatureGroup, CustomPane
from folium.plugins import MarkerCluster

from settings import settings

# logger
log = logging.getLogger(__name__)


# Modify Marker template to include the onClick event
click_template = """{% macro script(this, kwargs) %}
    var {{ this.get_name() }} = L.marker(
        {{ this.location|tojson }},
        {{ this.options|tojson }}
    ).addTo({{ this._parent.get_name() }}).on('click', onMarkerClick);
{% endmacro %}"""
folium.Marker._template = Template(click_template)  # pylint: disable=protected-access


class WebEnginePage(QWebEnginePage):
    """web engine and JS console"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def javaScriptConsoleMessage(
        self, level, msg, line, sourceID
    ):  # pylint: disable=unused-argument
        """receive message from JS console"""
        # print(f"level:{level} line:{line} source:{sourceID} msg:{msg}")
        self.parent.handleConsoleMessage(msg)


class WebView(QWebEngineView):
    """Webview"""

    def __init__(self, mapWidget):
        super().__init__()
        self.menu = None
        self.mapWidget = mapWidget

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.onContextMenu)

    def onContextMenu(self):
        """create context"""
        menu = QMenu()

        action = QAction(
            "Markers selection in views",
            self,
            triggered=self.mapWidget.markersToSelection,
        )
        menu.addAction(action)

        action = QAction(
            "Remove markers",
            self,
            triggered=self.mapWidget.removeMarkers,
            enabled=len(self.mapWidget.locs_photos) > 0,
        )
        menu.addAction(action)

        action = QAction(
            "Hide/Show cluster markers",
            self,
            triggered=self.mapWidget.toggleMarkers,
            enabled=len(self.mapWidget.locs_photos) > 0,
        )
        menu.addAction(action)

        action = QAction(
            "Use clustered markers",
            self,
            checkable=True,
            checked=self.mapWidget.use_cluster,
            triggered=lambda checked: self.mapWidget.setMapType(
                self.mapWidget.getMapType(), use_cluster=checked
            ),
        )
        menu.addAction(action)

        if settings.value("mapSaveHtml", 0) == 1:
            # for debug
            menu.addSeparator()
            action = QAction("Save to html", self, triggered=self.savePage)
            menu.addAction(action)

        menu.exec(QCursor.pos())

    def savePage(self):
        """save html on disk"""

        def done(html):
            with open("SOURCE_PAGE.html", "w", encoding="utf8") as f:
                f.write(html)
            log.info("Page html saved")

        self.page().toHtml(done)


class MapWidget(QtWidgets.QWidget):
    """Map widget class

    self.marker : current marker
    """

    markerClick = Signal(list)

    def __init__(self, map_type, use_marker_cluster=True):
        super().__init__()

        # during development : a fake map widget is possible
        self._fake = settings.value("useMapWidget", 1) == 0
        if self._fake:
            return

        self._page_loaded = False
        self._webview_destroyed = False
        self._waiting_locations = []
        self.map = None
        self.use_cluster = use_marker_cluster
        self.cluster = None
        self.currentGroup = None
        self._zoom = 5
        self.locs_photos = {}
        self._js_response = None

        self.window_width, self.window_height = 200, 200

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # create initial invisible marker
        self.marker = folium.Marker(
            location=[48.8529, 2.35], idphoto=0, icon=folium.Icon(color="red")
        )

        self.webView = WebView(self)  # start web engine
        self.webView.loadFinished.connect(self._on_load_finished)
        self.webView.setPage(WebEnginePage(self))

        layout.addWidget(self.webView)

        self.setMapType(map_type, self.use_cluster)

    def handleConsoleMessage(self, msg: str):
        """handle message on JS console"""
        try:
            key, value = msg.split(": ", maxsplit=1)
        except ValueError:
            print(msg)
            return
        if key == "location":
            data = json.loads(value)
            lat = data["lat"]
            lng = data["lng"]
            log.info("Map click : %s, %s", lat, lng)
            # TODO emit click_location signal
        elif key == "zoom":
            self._zoom = int(round(float(value)))
        elif key == "clickMarker":
            data = json.loads(value)
            lat = data["lat"]
            lng = data["lng"]
            log.info("Marker click : %s, %s", lat, lng)
        elif key == "idphoto":
            photo_id = json.loads(value)
            log.info("Marker photo_id : %s", photo_id)
            self.markerClick.emit(photo_id)
        elif key == "mapbounds":
            self._js_response = json.loads(value)
            log.info("handleConsole : %s", self._js_response)
        else:
            print(msg)

    def setMapType(self, map_type: str, use_cluster: bool = True):
        """set map type (tiles)"""
        if self._fake:
            return
        log.info("set map %s, cluster:%s", map_type, use_cluster)
        self.use_cluster = use_cluster
        self._page_loaded = False
        self.map_type = map_type

        self.map = folium.Map(
            tiles=map_type, zoom_start=self._zoom, location=self.marker.location
        )

        CustomPane("pane_cluster", 500).add_to(self.map)
        CustomPane("pane_current", 650).add_to(self.map)

        if self.use_cluster:
            self.cluster = MarkerCluster(
                name="cluster", clusterPane="pane_cluster"
            ).add_to(self.map)
        else:
            self.cluster = FeatureGroup(name="cluster", pane="pane_cluster").add_to(
                self.map
            )

        # re-create current marker
        self.currentGroup = FeatureGroup(name="current", pane="pane_current").add_to(
            self.map
        )
        self.marker.add_to(self.currentGroup)
        self.set_location(self.marker.location, 0, False)

        # Add Custom JS to folium map (click location)
        self._add_customjs()

        # save map data to data object
        data = io.BytesIO()
        self.map.save(data, close_file=False)

        self.webView.setHtml(data.getvalue().decode())

    def getMapType(self) -> str:
        """get map type (tiles)"""
        if self._fake:
            return None
        return self.map_type

    def _add_customjs(self):
        """add custom javascript to html page"""
        my_js = f"""
    {self.map.get_name()}.on("click",
        function (e) {{
            var data = `${{JSON.stringify(e.latlng)}}`;
            console.log("location:", data)
        }});

    {self.map.get_name()}.on("zoomend", function (e) {{
        console.log("zoom:", e.target._zoom);
    }});

    function onMarkerClick(e) {{
            var marker = e.target;
            console.log("typeof", typeof(e.target))
            var data = `${{JSON.stringify(marker.options.idphoto)}}`;
            console.log("idphoto:", data);
            }}

    function setClusterMarkers(datas) {{
        datas.forEach(elt => {{
            L.marker(elt[0], {{"idphoto":elt[1]}}).addTo({self.cluster.get_name()}).on('click', onMarkerClick);
        }})
    }}

    function hideCurrentLayer() {{
        if ({self.map.get_name()}.hasLayer({self.currentGroup.get_name()})) {{
           // console.log("current layer active, remove it");
            {self.map.get_name()}.removeLayer({self.currentGroup.get_name()})
        }} else {{
            // console.log("no current layer, ignore");
        }}
    }}

    function showCurrentLayer() {{
        if ({self.map.get_name()}.hasLayer({self.currentGroup.get_name()})) {{
            //console.log("current layer active, ignore");
            return;
        }} else {{
            //console.log("no current layer, add it");
            {self.currentGroup.get_name()}.addTo({self.map.get_name()})
        }}
    }}

    function toggleClusterLayer() {{
        if ({self.map.get_name()}.hasLayer({self.cluster.get_name()})) {{
            console.log("cluster layer active: remove it");
            {self.map.get_name()}.removeLayer({self.cluster.get_name()})
        }} else {{
            console.log("no cluster layer: add it");
            {self.cluster.get_name()}.addTo({self.map.get_name()})
        }}
    }}

    function getMapBounds() {{
        var bounds = {self.map.get_name()}.getBounds();
        var data = `${{JSON.stringify(bounds)}}`;
        console.log("mapbounds:", data)
    }}
        """

        e = Element(my_js)
        html = self.map.get_root()
        html.script.get_root().render()
        # Insert new element or custom JS
        html.script._children[e.get_name()] = e  # pylint: disable=protected-access

    def set_location(self, new_coords: tuple[float, float], photo_id: int, flyto: bool):
        """
        change location of current marker
        """
        if self._fake:
            return
        if not self._page_loaded:
            # differed set location
            log.info("differed set_location")
            if self._waiting_locations:
                # at this moment, differs only one call
                self._waiting_locations = []
                log.info("delete previous location")
            self._waiting_locations.append(("location", photo_id, new_coords, flyto))
            return

        if isinstance(new_coords, folium.Marker):
            new_coords = new_coords.location
        elif new_coords[0] is None or new_coords[1] is None:
            self.hide_current_location()
            return
        js_code = f"""
            hideCurrentLayer();
            {self.marker.get_name()}.setLatLng({list(new_coords)});
            {self.map.get_name()}.{"flyTo" if flyto else "panTo"}({list(new_coords)});
            {self.marker.get_name()}.options.idphoto = [{photo_id}];
            showCurrentLayer();
            """
        self.webView.page().runJavaScript(js_code)
        self.marker.location = new_coords

    def set_locations(self, coords: list[tuple[int, tuple[float, float]]]):
        """
        set multiple locations: new map builded
        """
        if self._fake:
            return
        if not coords:
            return
        self.locs_photos = {}
        self.removeMarkers()

        for photo_id, location in coords:
            if location in self.locs_photos:
                self.locs_photos[location].append(photo_id)
            else:
                self.locs_photos[location] = [photo_id]
        self._set_locations()

    def _set_locations(self):
        """set locations from internal self.set_location dict"""
        if not self.locs_photos:
            return
        js_datas = []
        for location, ids in self.locs_photos.items():
            js_datas.append((location, ids))
        js_code = f"""locdatas = {json.dumps(js_datas)};
        setClusterMarkers(locdatas);"""
        self.webView.page().runJavaScript(js_code)

    def hide_current_location(self):
        """
        hide current marker
        """
        if self._fake:
            return
        js_code = "hideCurrentLayer();"
        self.webView.page().runJavaScript(js_code)

    def _on_load_finished(self, ok: bool):
        """signal page loaded"""
        if not ok:
            log.error("Failed to load map")
        else:
            log.info("map page loaded %s", ok)
        self._page_loaded = True
        # differed locations to set
        if self._waiting_locations:
            log.info("set waiting location")
            func_name, photo_id, locations, flyto = self._waiting_locations[0]
            if func_name == "location":
                self.set_location(locations, photo_id, flyto)
            self._waiting_locations = []
        # restore markers
        self._set_locations()

    def markersToSelection(self):
        """send selection for all markers to views"""
        ids = []
        for _, idsloc in self.locs_photos.items():
            ids.extend(idsloc)
        self.markerClick.emit(ids)

    def toggleMarkers(self):
        """toggle show cluster markers"""
        self.webView.page().runJavaScript("toggleClusterLayer();")

    def removeMarkers(self):
        """remove markers from cluster layer"""
        if self._fake or not self._page_loaded:
            return
        self.locs_photos = {}
        js_code = f"""
            {self.cluster.get_name()}.clearLayers();
            """
        self.webView.page().runJavaScript(js_code)

        js_code += f"""
            hideCurrentLayer();
            //{self.currentGroup.get_name()}.clearLayers();
        """
        self.webView.page().runJavaScript(js_code)

    def setUseMarkerCluster(self, checked):
        """use cluster of markers"""
        self.setMapType(self.mapWidget.getMapType(), use_cluster=checked)

    # def _wait_js_response(self):
    def _js_command_wait_response(self, command: str, timeout: int = 500) -> dict:
        """Launch javascript command and wait for response in self._js_response.
        timeout is in ms

        Response from command set self._js_response in handleConsoleMessage
        """
        timeout = float(timeout) / 1000
        self._js_response = None
        log.info("JS command %s", command)
        self.webView.page().runJavaScript(command)
        t0 = time.time()
        while True:
            QApplication.instance().processEvents(
                QEventLoop.ProcessEventsFlag.AllEvents
            )
            if self._js_response is not None:
                break
            if time.time() - t0 > timeout:
                log.error("JS response timeout")
                raise TimeoutError
        log.info("JS response ready")
        return self._js_response

    def get_map_bounds(self) -> dict:
        """return current map bounds"""
        try:
            return self._js_command_wait_response("getMapBounds();")
        except TimeoutError:
            pass
        return None
