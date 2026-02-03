# -*- encoding: utf-8 -*-
# pylint: disable=too-many-lines,line-too-long,invalid-name,attribute-defined-outside-init,wrong-import-position


"""

Lightroom Viewer Application

"""
import os
import sys
import logging
import argparse
import ctypes
import weakref
from enum import StrEnum

from PySide6.QtWidgets import (
    QApplication,
    QMdiArea,
    QMdiSubWindow,
    QAbstractItemView,
    QLineEdit,
    QSplitter,
    QMainWindow,
    QWidget,
    QToolButton,
    QMenu,
    QDockWidget,
    QFileDialog,
    QComboBox,
    QMessageBox,
    QLabel,
)
from PySide6.QtGui import (
    QGuiApplication,
    QIcon,
    QCursor,
    QAction,
)
from PySide6.QtCore import (
    Qt,
    QModelIndex,
    QItemSelectionModel,
    QItemSelection,
    QItemSelectionRange,
)

import qdarktheme

from lrtools import __version__ as LRTOOLS_VERSION


# local imports
sys.path.append(os.path.realpath(os.path.dirname(__file__)))

from settings import settings, APP_NAME, APP_VERSION
from modelPhotos import PhotosModel
from collectionsWidget import CollectionsFilterWidget
from modelCollections import CollectionsModel, ItemType, TreeItem
from photosThumbView import PhotosThumbView
from photosListView import PhotosListView
from metadatasView import MetadatasView
from lrApi import PhotoMetadatas, criteria_to_dict, dict_to_criteria, lr_api
from thumbProvider import thumbs_provider

from slideshow.slideshow import SlideShow
from loggerWidget import LoggerWidget
from comboHist import ComboHistory
from imageWidget import ImageWidget
from mapWidget import MapWidget

from uiDialogs import AboutDialog
from dlgColumns import ColumnsDialog
from dlgCriteria import CriteriaDialog


STATUS_LABEL_COUNT = "Photos count: {0}"
STATUS_LABEL_SELECTED = "Selected count: {0}"

ROOT_QUERY = "Query:/"
ROOT_FOLDER = "Folders:/"
ROOT_COLLECTION = "Collections:/"
ROOT_PUBCOLLECTION = "Published:/"
ROOT_KEYWORD = "Keywords:/"
ROOT_SEARCH = "Search:/"


class WHERE_SEARCH(StrEnum):
    """search combo value"""

    ANY = "Any"
    FILENAME = "Filename"
    # FILECOPY = "Copy Filename"
    TITLE = "Title"
    CAPTION = "Caption"
    # META_ANY = "Any Metadatas"
    META_EXIF = "EXIF"
    META_IPTC = "IPTC"


# set logger in stdout
log = logging.getLogger("lrviewer")
log.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(
    logging.Formatter(
        "%(name)s - %(asctime)s.%(msecs)d - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
)
log.addHandler(handler)
log.info("Logger in place")


def abspath(filename):
    """return absolutepath from relative filename"""
    return os.path.join(os.path.realpath(os.path.dirname(__file__)), filename)


class App(QMainWindow):
    """
    main application
    """

    def __init__(self, args: argparse.Namespace):
        """init main windows"""
        super().__init__()

        # Application icon
        self.setWindowIcon(QIcon(abspath("./ico/lrviewer48x48.png")))
        if sys.platform == "win32":
            # show correct icon in taskbar
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "fdenivac.lrviewer"
            )

        self.mdi = QMdiArea()
        self.setCentralWidget(self.mdi)

        self.setHidden(settings.value("hideMainWindowOnInit", 0))

        self.initUI()

        self.statusBar().showMessage(f"Welcome to {APP_NAME} version {APP_VERSION}")
        self.updateToolbar()

        lr_api.default_columns = settings.value(
            "defaultColumns", "name,datecapt,speed,aperture,iso"
        )

        if args.lrcat:
            self.openLrCatalog(args.lrcat, args.columns, args.criteria)
        else:
            recent = self.recentCatalog()
            if recent:
                self.openLrCatalog(recent, args.columns, args.criteria)
            else:
                self.show()
                self.openLrCatalogDlg()

        if args.slideshow:
            self.slideshow.setInterval(args.timer * 1000)
            self.toggleSlideshowFullScreen()
            self.onStartSlideshow()
        else:
            self.show()

    def initUI(self):
        """
        init User Interface
        """
        # logging windows
        if settings.value("UseLogWidget", 1):
            self.log_dock = QDockWidget("Log window")
            self.log_dock.setObjectName("logs_dock")
            self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
            self.logTextBox = LoggerWidget(self)
            logging.getLogger().addHandler(self.logTextBox)
            logging.getLogger().setLevel(logging.INFO)
            self.log_view = self.logTextBox
            self.log_dock.setWidget(self.logTextBox)
            self.restoreDockWidget(self.log_dock)
        log.info("starting %s version %s", APP_NAME, APP_VERSION)
        log.info("lrtools version : %s", LRTOOLS_VERSION)

        # customize status bar
        statusbar = self.statusBar()
        self.label_photos_count = QLabel(STATUS_LABEL_COUNT.format(0))
        statusbar.addPermanentWidget(self.label_photos_count)
        self.label_photos_selected = QLabel(STATUS_LABEL_SELECTED.format(0))
        statusbar.addPermanentWidget(self.label_photos_selected)

        # create tree for the various collections
        #   (collections are lightroom keywords, collections, smart collections, published collections and lrviewer queries)
        self.collections_dock = QDockWidget("Collections")
        self.collections_dock.setObjectName("collections_dock")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.collections_dock)
        self.collectionsView = CollectionsFilterWidget()
        self.collectionsView.selectCollection.connect(self.onSelectCollection)
        self.collectionsView.queryUnstored.connect(self.onQueryUnstored)
        self.collections_dock.setWidget(self.collectionsView)
        self.restoreDockWidget(self.collections_dock)

        # Dock metadatas
        self.metadatas_dock = QDockWidget("Metadatas")
        self.metadatas_dock.setObjectName("metadatas_dock")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.metadatas_dock)
        self.metadatas_view = MetadatasView()
        self.metadatas_dock.setWidget(self.metadatas_view)
        self.restoreDockWidget(self.metadatas_dock)

        # Dock image widget
        self.thumbnail_dock = QDockWidget("Photo Thumbnail")
        self.thumbnail_dock.setObjectName("thumbnail_dock")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.thumbnail_dock)
        self.thumbnailWidget = ImageWidget(self)
        self.thumbnail_dock.setWidget(self.thumbnailWidget)
        self.thumbnailWidget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.restoreDockWidget(self.thumbnail_dock)

        # Dock slideshow widget
        self.slideshow_dock = QDockWidget("Slideshow")
        self.slideshow_dock.setObjectName("slideshow_dock")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.slideshow_dock)
        self.slideshow = self.createSlideshowWidget()
        self.slideshow_dock.setWidget(self.slideshow)
        self.restoreDockWidget(self.slideshow_dock)
        self.stateSlideshowFloating = self.slideshow_dock.isFloating()

        # Dock geo map
        map_type = settings.value("mapTiles", "OpenStreetMap")
        self.map_dock = QDockWidget(f'Map "{map_type}"')
        self.map_dock.setObjectName("metadatas_dock")
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.map_dock)
        self.mapWidget = MapWidget(map_type, settings.value("mapUseCluster", 1) == 1)
        self.map_dock.setWidget(self.mapWidget)
        self.restoreDockWidget(self.map_dock)
        self.mapWidget.markerClick.connect(self.onMapMarker)

        # create PhotoMetadatas instance (class inherited of PhotosApi) for retrieving metadatas for unique photo
        # connexion to database will be cloned from lr_api on open lightroom catalog
        self.photo_metadatas = PhotoMetadatas()

        # create photos model used by photosListView and photosThumbView
        self.photoModel = PhotosModel()

        # Create MDI sub-window photos list
        self.photosListView = self.createPhotoListView()
        self.mdiPhotosList = self.createMDIView(self.photosListView, "Photos List")

        # Create MDI sub-window photos thumnbail
        self.photosThumbView = self.createPhotosThumbView()
        self.mdiPhotosThumb = self.createMDIView(self.photosThumbView, "Photos Thumb")

        self.lastSubWindowActived = None

        # create top menus
        self.createTopMenu()

        # creation tools bar
        self.createActionBar()

        # restore windows/state positions
        self.restoreGeometry(settings.value("winMainPos", bytes("", "utf-8")))
        self.restoreState(settings.value("winMainState", bytes("", "utf-8")))

        # restore, maximize last MDI activated
        if settings.value("activeMDI", "PhotosList") == "PhotosList":
            self.activatePhotosList(True)
        else:
            self.activatePhotosThumb(True)
        self.mdi.activeSubWindow().showMaximized()

        self.updateToolbar()

        log.info("END InitUI")

    def createTopMenu(self):
        """create initial menus"""
        # Add menus
        menuBar = self.menuBar()

        fileMenu = menuBar.addMenu("&File")
        editMenu = menuBar.addMenu("&Edit")
        queryMenu = menuBar.addMenu("&Query")
        viewMenu = menuBar.addMenu("&View")
        mapMenu = menuBar.addMenu("&Map")
        slideshowMenu = menuBar.addMenu("&Slideshow")
        helpMenu = menuBar.addMenu("&Help")

        # connect aboutToShow signal for update menus
        editMenu.aboutToShow.connect(self.updateEditMenu)
        viewMenu.aboutToShow.connect(self.updateViewMenu)
        queryMenu.aboutToShow.connect(self.updateQueryMenu)
        mapMenu.aboutToShow.connect(self.updateMapMenu)
        slideshowMenu.aboutToShow.connect(self.updateSlideshowMenu)

        # File
        #
        action = QAction("&Open Lightroom catalog ...", self)
        action.triggered.connect(self.openLrCatalogDlg)
        fileMenu.addAction(action)
        self.recentCatalogsMenu = fileMenu.addMenu("&Open Recent Catalog")
        self.recentCatalogsMenu.triggered.connect(self.onRecentCatalog)
        # restore recent catalogs
        self.restoreRecentCatalogs()

        fileMenu.addSeparator()

        action = QAction("&Quit", self)
        action.triggered.connect(self.quitApp)
        action.setShortcut("Ctrl+Q")
        action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        fileMenu.addAction(action)

        # Edit
        #
        action = QAction("&Select All", self)
        action.setStatusTip("Select All")
        action.setShortcut("Ctrl+A")
        action.triggered.connect(self.selectAll)
        editMenu.addAction(action)

        action = QAction("&Unselect All", self)
        action.setStatusTip("Unselect All")
        action.setShortcut("Ctrl+D")
        action.triggered.connect(self.unselectAll)
        editMenu.addAction(action)

        # Query
        #
        action = QAction("Query All", self)
        action.setStatusTip("Query all (photos and videos)")
        action.triggered.connect(self.queryAll)
        queryMenu.addAction(action)

        action = QAction("Query All Photos", self)
        action.setStatusTip("Query all photos")
        action.triggered.connect(self.queryAllPhotos)
        queryMenu.addAction(action)

        queryMenu.addSeparator()

        action = QAction("Store Current Query ...", self)
        action.setStatusTip("Store current query in collections panel")
        action.triggered.connect(self.collectionsView.onStoreQuery)
        # action.triggered.connect(self.onStoreQuery)
        queryMenu.addAction(action)

        action = QAction("Create Query ...", self)
        action.setStatusTip("Open dialog create query")
        action.triggered.connect(self.onCreateQuery)
        queryMenu.addAction(action)
        self.actionQuery = action

        self.actionQueryCreateColl = QAction("Create Query Collection ...", self)
        self.actionQueryCreateColl.setStatusTip("create collection of queries")
        self.actionQueryCreateColl.triggered.connect(self.onCreateQueryCollection)
        queryMenu.addAction(self.actionQueryCreateColl)

        self.actionRenameQuery = QAction("Rename Query ...", self)
        self.actionRenameQuery.setStatusTip("Rename a stored query")
        self.actionRenameQuery.triggered.connect(self.onRenameQuery)
        queryMenu.addAction(self.actionRenameQuery)

        self.actionRemoveQuery = QAction("Remove Query", self)
        self.actionRemoveQuery.setStatusTip("Remove this a stored query")
        self.actionRemoveQuery.triggered.connect(self.onRemoveQuery)
        queryMenu.addAction(self.actionRemoveQuery)

        queryMenu.addSeparator()

        self.action = QAction("Load Queries ...", self)
        self.action.setStatusTip("Load queries from file")
        self.action.triggered.connect(self.onLoadQueries)
        queryMenu.addAction(self.action)

        self.action = QAction("Load & Merge Queries ...", self)
        self.action.setStatusTip("Load and merge with current queries from file")
        self.action.triggered.connect(
            lambda merge, m=True: self.onLoadQueries(None, merge=m)
        )
        queryMenu.addAction(self.action)

        self.action = QAction("Save Queries ...", self)
        self.action.setStatusTip("Save queries on disk")
        self.action.triggered.connect(self.collectionsView.onSaveQueries)
        queryMenu.addAction(self.action)

        queryMenu.addSeparator()

        action = QAction("Columns Selection ...", self)
        action.setStatusTip("Open dialog for columns selection")
        action.triggered.connect(self.selectColumns)
        queryMenu.addAction(action)

        action = QAction("Criterias Selection ...", self)
        action.setStatusTip("Open dialog for criterias selection")
        action.triggered.connect(self.selectCriterias)
        queryMenu.addAction(action)

        action = QAction("Set Default Columns ...", self)
        action.setStatusTip("Default columns used in some situations")
        action.triggered.connect(self.selectDefaultColumns)
        queryMenu.addAction(action)

        # Map
        #
        subMenu = QMenu("Map Types", self, statusTip="Select the type of map")
        for map_type in ["OpenStreetMap", "OpenTopoMap", "GeoportailFrance.plan"]:
            action = QAction(
                map_type,
                self,
                checkable=True,
                triggered=lambda setmap, map=map_type: self.onSetMapType(map),
            )
            subMenu.addAction(action)
        mapMenu.addMenu(subMenu)
        self.menuMapTypes = subMenu

        mapMenu.addSeparator()

        self.actionQueryToMap = QAction(
            "Show query locations",
            self,
            statusTip="Show GPS locations for complete query results",
            triggered=self.onShowQueryLocations,
        )
        mapMenu.addAction(self.actionQueryToMap)

        self.actionSelectedToMap = QAction(
            "Show selection locations",
            self,
            statusTip="Show GPS locations for current selected photos",
            triggered=self.onShowSelectedLocations,
        )
        mapMenu.addAction(self.actionSelectedToMap)

        action = QAction(
            "Query photos from map bounds",
            self,
            statusTip="Query photos from visible map bounds. Show markers on map when Control key actived",
            triggered=self.onSelectedVisiblePhotos,
        )
        mapMenu.addAction(action)

        mapMenu.addSeparator()

        self.actionMapFlyto = QAction(
            "Use Fly To",
            self,
            statusTip="Use fly to new position (nice, but long)",
            checkable=True,
            checked=settings.value("mapFlyTo", 0),
        )
        mapMenu.addAction(self.actionMapFlyto)

        self.actionMapCluster = QAction(
            "Use Markers Cluster",
            self,
            statusTip="Use cluster of markers",
            checkable=True,
            checked=settings.value("mapUseCluster", 1),
            triggered=self.setUseMarkerCluster,
        )
        mapMenu.addAction(self.actionMapCluster)

        # View
        #
        self.actionActivatePhotosList = QAction(
            "Photos List",
            self,
            statusTip="Active Photos List view",
            shortcut="Ctrl+L",
            triggered=self.activatePhotosList,
            checkable=True,
        )
        viewMenu.addAction(self.actionActivatePhotosList)

        self.actionActivatePhotosThumb = QAction(
            "Photos Thumbnails",
            self,
            statusTip="Active Photos Thumbnail view",
            shortcut="Ctrl+T",
            triggered=self.activatePhotosThumb,
            checkable=True,
        )
        viewMenu.addAction(self.actionActivatePhotosThumb)

        viewMenu.addSeparator()

        self.actionTile = QAction(
            "&Tile",
            self,
            statusTip="Tile the windows",
            triggered=self.mdi.tileSubWindows,
        )
        viewMenu.addAction(self.actionTile)

        self.actionCascade = QAction(
            "&Cascade",
            self,
            statusTip="Cascade the windows",
            triggered=self.mdi.cascadeSubWindows,
        )
        viewMenu.addAction(self.actionCascade)

        viewMenu.addSeparator().setText("Dock Views")

        # collections view
        self.actionShowCollectionsView = QAction(
            "Collections View",
            self,
            statusTip="Show/Hide Collections",
            checkable=True,
            triggered=self.showCollectionsView,
        )
        viewMenu.addAction(self.actionShowCollectionsView)

        self.actionMetadatasView = QAction(
            "Metadatas view",
            self,
            statusTip="Show/Hide Metadatas view",
            checkable=True,
            triggered=self.showMetadatasView,
        )
        viewMenu.addAction(self.actionMetadatasView)

        self.actionThumbView = QAction(
            "&Thumbnail view",
            self,
            statusTip="Show/Hide Thumbnail view",
            checkable=True,
            triggered=self.showThumbView,
        )
        viewMenu.addAction(self.actionThumbView)

        self.actionShowSlideshow = QAction(
            "Slideshow view",
            self,
            statusTip="Show/hide Slideshow view",
            checkable=True,
            triggered=self.showSlideshowView,
        )
        viewMenu.addAction(self.actionShowSlideshow)

        self.actionMapView = QAction(
            "Map view",
            self,
            statusTip="Show/Hide Map view",
            checkable=True,
            triggered=self.showMapView,
        )
        viewMenu.addAction(self.actionMapView)

        if settings.value("UseLogWidget", 1):
            self.actionLogView = QAction(
                "&Log view",
                self,
                statusTip="Show Log view",
                checkable=True,
                triggered=self.showLogView,
            )
            viewMenu.addAction(self.actionLogView)

        viewMenu.addSeparator()

        # hide/display components in MDI Area

        self.actionShowPhotosList = QAction(
            "Show/Hide Photos List",
            self,
            statusTip="Show/hide Photos List",
            checkable=True,
            triggered=self.showHidePhotoList,
        )
        viewMenu.addAction(self.actionShowPhotosList)

        self.actionShowPhotosThumb = QAction(
            "Show/Hide Photos Thumb",
            self,
            statusTip="Show/hide Photos Thumb",
            checkable=True,
            triggered=self.showHidePhotoThumb,
        )
        viewMenu.addAction(self.actionShowPhotosThumb)

        viewMenu.addSeparator()

        # option thumbnail in PhotoListView first column
        self.actionThumbsInPhotoList = QAction(
            "Thumbnail in Photos list",
            self,
            statusTip="Show/hide Tumbnails",
            checkable=True,
            triggered=self.onShowThumbsInPhotosList,
        )
        viewMenu.addAction(self.actionThumbsInPhotoList)

        # Slideshow Menu
        #

        # start slide show from first photo
        self.actionStartSlideshow = QAction(
            "Start slideshow (from first photo)",
            self,
            statusTip="Start slideshow from first photo",
            triggered=self.onStartSlideshow,
        )
        slideshowMenu.addAction(self.actionStartSlideshow)

        # continue slide show
        self.actionContinueSlideShow = QAction(
            "Start slideshow from current photo",
            self,
            statusTip="Continue slideshow of current folder",
            triggered=self.onContinueSlideshow,
        )
        slideshowMenu.addAction(self.actionContinueSlideShow)

        # pause slide show
        self.actionPauseSlideshow = QAction(
            "Pause slideshow",
            self,
            statusTip="Pause slideshow of current folder",
            triggered=self.onPauseSlideshow,
        )
        slideshowMenu.addAction(self.actionPauseSlideshow)

        # slide show delay between photos
        subMenu = QMenu("Slideshow speed", self, statusTip="Adjust slideshow speed")
        for delay in [3, 5, 10, 15]:
            action = QAction(
                f"{delay} seconds",
                self,
                checkable=True,
                triggered=lambda setspeed, speed=delay: self.onSetSlideshowSpeed(speed),
            )
            action.setData(delay * 1000)
            subMenu.addAction(action)
        slideshowMenu.addMenu(subMenu)
        self.menuSlideshowSpeed = subMenu

        slideshowMenu.addSeparator()

        # fullscreen toggle
        self.actionSlideshowFullscreen = QAction(
            "Fullscreen",
            self,
            statusTip="Full Screen Toggle",
            shortcut="Ctrl+F",
            shortcutContext=Qt.ShortcutContext.ApplicationShortcut,
            triggered=self.toggleSlideshowFullScreen,
        )
        slideshowMenu.addAction(self.actionSlideshowFullscreen)

        # About Menu
        #
        action = QAction(
            "&About",
            self,
            statusTip="About LrViewer",
            triggered=self.about,
        )
        helpMenu.addAction(action)

        app = QApplication.instance()
        helpMenu.addAction("About Qt", app.aboutQt)
        action.setStatusTip("About Qt framework")

    def createActionBar(self):
        """initial action bar"""
        self.toolbar = self.addToolBar("actionToolBar")
        self.toolbar.setObjectName("action_toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)

        # navigation icons
        self.btBack = QToolButton()
        self.btBack.setIcon(QIcon(abspath("./ico/arrow-180.png")))
        self.btBack.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btBack.setStatusTip("Navigate Previous address")
        self.btBack.clicked.connect(self.navigateBack)
        self.toolbar.addWidget(self.btBack)

        self.btForward = QToolButton()
        self.btForward.setIcon(QIcon(abspath("./ico/arrow.png")))
        self.btForward.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.btForward.setStatusTip("Navigate Next address")
        self.btForward.clicked.connect(self.navigateForward)
        self.toolbar.addWidget(self.btForward)

        # splitter for address bar, search, combo search space
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.addressBar = ComboHistory(fixCase=settings.value("FixHistCase", 0))
        self.addressBar.activated.connect(self.onUrlActivated)
        splitter.addWidget(self.addressBar)

        # search section
        self.searchField = QLineEdit()
        self.searchField.setPlaceholderText("Search")
        self.searchField.returnPressed.connect(self.onSearch)
        splitter.addWidget(self.searchField)

        self.searchWhere = QComboBox()
        for text in WHERE_SEARCH:
            self.searchWhere.addItem(text.value)
        self.searchWhere.setEditable(False)
        splitter.addWidget(self.searchWhere)

        splitter.setStretchFactor(10, 1)
        splitter.setSizes([500, 200, 100])

        self.toolbar.addWidget(splitter)

        self.btPhotosList = QToolButton(
            icon=QIcon(abspath("./ico/winlist.png")),
            statusTip="Activate Photos List",
            toolButtonStyle=Qt.ToolButtonStyle.ToolButtonIconOnly,
            checkable=True,
            clicked=lambda setview, view="list": self.changeView(view),
        )
        self.btPhotosList.setStyleSheet("QToolButton { border: 0px }")
        self.toolbar.addWidget(self.btPhotosList)

        self.btPhotosThumb = QToolButton(
            icon=QIcon(abspath("./ico/winicons.png")),
            statusTip="Activate Photos Thumbnails List",
            toolButtonStyle=Qt.ToolButtonStyle.ToolButtonIconOnly,
            checkable=True,
            clicked=lambda setview, view="thumbs": self.changeView(view),
        )
        self.btPhotosThumb.setStyleSheet("QToolButton { border: 0px }")
        self.toolbar.addWidget(self.btPhotosThumb)

        self.toolbar.setStyleSheet("QToolBar { border: 0px }")

    def createMDIView(self, widget: QWidget, title: str):
        """Create MDI sub-window photos list"""
        sub = QMdiSubWindow()
        sub.setWidget(widget)
        sub.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        sub.setWindowTitle(title)
        self.mdi.addSubWindow(sub)
        sub.setWindowFlags(
            Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowMaximizeButtonHint
        )
        sub.show()
        widget.show()
        return sub

    def createPhotoListView(self):
        """Create photo list view"""
        view = PhotosListView(self.photoModel)
        view.horizontalHeader().sortIndicatorChanged.connect(
            self.onSortIndicatorChanged
        )

        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.customContextMenuRequested.connect(self.photosContextItemMenu)
        view.selectionModel().currentRowChanged.connect(self.onPhotoRowChanged)
        view.selectionModel().selectionChanged.connect(self.onSelectionChanged)
        view.doubleClicked.connect(self.onPhotoDoubleClicked)
        view.hide()
        return view

    def createPhotosThumbView(self):
        """create photos thumb view"""
        view = PhotosThumbView(self.photoModel)
        view.selectionModel().currentRowChanged.connect(self.onPhotoRowChanged)
        view.doubleClicked.connect(self.onPhotoDoubleClicked)
        view.hide()
        return view

    ##############################################################
    #
    # Update UI
    #
    ##############################################################

    def updateQueryMenu(self):
        """update Query menu"""
        self.actionQuery.setEnabled(True)
        index = self.collectionsView.currentQueryIndex()
        enable = index.isValid()
        self.actionRenameQuery.setEnabled(enable)
        self.actionRemoveQuery.setEnabled(enable)

    def updateEditMenu(self):
        """update edit menu"""

    def updateMapMenu(self):
        """update edit menu"""
        for action in self.menuMapTypes.actions():
            action.setChecked(action.text() == self.mapWidget.getMapType())
        self.actionQueryToMap.setEnabled(lr_api.has_id_column())

    def updateSlideshowMenu(self):
        """update slideshow menu"""
        name = "Exit Fullscreen" if self.slideshow_dock.isFullScreen() else "Fullscreen"
        self.actionSlideshowFullscreen.setText(name)
        self.actionPauseSlideshow.setEnabled(self.slideshow.isTimerActive())
        delay = self.slideshow.getInterval()
        for action in self.menuSlideshowSpeed.actions():
            action.setChecked(action.data() == delay)
        enable = lr_api.has_id_column()
        self.actionStartSlideshow.setEnabled(enable)
        self.actionContinueSlideShow.setEnabled(enable)

    def updateViewMenu(self):
        """update edit menu"""
        self.actionActivatePhotosList.setChecked(
            not self.mdiPhotosList.isHidden()
            and self.mdi.activeSubWindow() == self.mdiPhotosList
        )
        self.actionActivatePhotosThumb.setChecked(
            not self.mdiPhotosThumb.isHidden()
            and self.mdi.activeSubWindow() == self.mdiPhotosThumb
        )
        self.actionShowPhotosList.setChecked(not self.mdiPhotosList.isHidden())
        self.actionShowPhotosThumb.setChecked(not self.mdiPhotosThumb.isHidden())
        self.actionShowPhotosThumb.setEnabled(thumbs_provider.has_thumbs)
        self.actionShowPhotosList.setEnabled(thumbs_provider.has_thumbs)
        self.actionActivatePhotosList.setEnabled(thumbs_provider.has_thumbs)
        self.actionActivatePhotosThumb.setEnabled(thumbs_provider.has_thumbs)

        if settings.value("UseLogWidget", 1):
            self.actionLogView.setChecked(not self.log_dock.isHidden())
        self.actionShowCollectionsView.setChecked(not self.collections_dock.isHidden())
        self.actionMetadatasView.setChecked(not self.metadatas_dock.isHidden())
        self.actionThumbView.setChecked(not self.thumbnail_dock.isHidden())
        self.actionShowSlideshow.setChecked(not self.slideshow_dock.isHidden())
        self.actionMapView.setChecked(not self.map_dock.isHidden())

        self.actionThumbsInPhotoList.setEnabled(thumbs_provider.has_thumbs)

    def updateToolbar(self):
        """update toolbar status"""

        self.btBack.setDisabled(self.addressBar.isLast())
        self.btForward.setDisabled(self.addressBar.isFirst())

    def updateAfterQuery(self, setSort: bool = True, setFirst: bool = True):
        """
        update photos views, status bar after LR query
        """
        log.info("updateAfterQuery")

        self.statusBar().showMessage(
            f"Query failed: {lr_api.exception}" if lr_api.exception else ""
        )
        self.label_photos_count.setText(f"Photos count: {lr_api.query_count()}")

        # reset model (at least, needed for update scrollbar when count changed)
        self.photosListView.model().modelReset.emit()
        self.photosThumbView.model().modelReset.emit()

        # no "id" columns in lr_api, means no photos, so adjust photos list
        if self.actionThumbsInPhotoList.isChecked():
            self.photosListView.useThumbs(
                lr_api.has_id_column() and thumbs_provider.has_thumbs
            )

        # update sort indicator of photos view
        if setSort:
            sort_column = lr_api.sort_column_index()
            sort_index = abs(sort_column)
            sort_order = (
                Qt.SortOrder.DescendingOrder
                if sort_column > 0
                else Qt.SortOrder.AscendingOrder
            )
            self.setSortIndicator(sort_index, sort_order)
            log.info("setSortIndicator %s %s", sort_index, sort_order)

        self.photosListView.update()
        self.photosThumbView.update()
        self.mapWidget.removeMarkers()

        if setFirst:
            self.setphotosViewIndex("first")

        self.updateToolbar()

        self.photosListView.resizeColumnsToWindow()

    ##############################################################
    #
    # Methods standards
    #
    ##############################################################

    def about(self):
        """dialog about app"""
        AboutDialog(self).exec()

    def selectAll(self):
        """select all in main explorer"""
        self.photosListView.selectAll()

    def unselectAll(self):
        """unselect all in main explorer"""
        self.photosListView.selectionModel().clearSelection()

    def quitApp(self):
        """action quit application"""
        self.close()

    def closeEvent(self, event):
        """
        close app
        """

        # last chance to save queries
        if not self.lastChanceToSaveQueries():
            event.ignore()
            return

        # exit from fullscreen
        if self.slideshow_dock.isFullScreen():
            self.toggleSlideshowFullScreen()

        # save geometry on close
        settings.setValue("winMainPos", self.saveGeometry())
        settings.setValue("winMainState", self.saveState())

        active_mdi = self.mdi.activeSubWindow()
        if active_mdi:
            settings.setValue(
                "activeMDI",
                (
                    "PhotosList"
                    if isinstance(active_mdi.widget(), PhotosListView)
                    else "PhotosThumb"
                ),
            )

        self.saveRecentCatalogs()

        if not lr_api.exception:
            # TODO "lastQuery" to use
            settings.setValue(
                "lastQuery",
                f"Query:/{lr_api.criteria()}?{lr_api.columns(visible_col=True)}",
            )

        if settings.value("useLogWidget", 1):
            wr = weakref.ref(self.logTextBox)
            logging._removeHandlerRef(wr)  # pylint: disable=protected-access

        settings.setValue("mapFlyTo", int(self.actionMapFlyto.isChecked()))
        settings.setValue("mapUseCluster", int(self.actionMapCluster.isChecked()))

        super().closeEvent(event)

    ##############################################################
    #
    # Methods change/set, show/hide views
    #
    ##############################################################

    def activatePhotosList(self, check):
        """activate photos list"""
        self.copyViewSelection()
        self.mdi.setActiveSubWindow(self.mdiPhotosList)
        self.mdiPhotosList.setHidden(not check)
        self.btPhotosList.setChecked(True)
        self.btPhotosThumb.setChecked(False)

    def activatePhotosThumb(self, check):
        """activate photos thumb"""
        self.copyViewSelection()
        self.mdi.setActiveSubWindow(self.mdiPhotosThumb)
        self.mdiPhotosThumb.setHidden(not check)
        self.btPhotosThumb.setChecked(True)
        self.btPhotosList.setChecked(False)

    def changeView(self, view):
        """change active windows"""
        if view == "thumbs":
            self.activatePhotosThumb(True)
        elif view == "list":
            self.activatePhotosList(True)

    def copyViewSelection(self):
        """copy selection from view to view"""
        # clear current selection
        win_src = self.activeMainWindow()
        if not win_src:
            return
        win_dest = (
            self.photosThumbView
            if isinstance(win_src, PhotosListView)
            else self.photosListView
        )
        selection = win_src.selectionModel().selection()
        win_dest.selectionModel().select(
            selection,
            QItemSelectionModel.SelectionFlag.ClearAndSelect
            | QItemSelectionModel.SelectionFlag.Rows,
        )
        win_dest.selectionModel().setCurrentIndex(
            win_src.selectionModel().currentIndex(),
            QItemSelectionModel.SelectionFlag.Current
            | QItemSelectionModel.SelectionFlag.Rows,
        )

    def showSlideshowView(self, event):
        """show slideshow view"""
        self.slideshow_dock.setHidden(not event)
        if event:
            # because no photo set when invisible, force display current photo
            self.setphotosViewIndex("current")

    def showCollectionsView(self, event):
        """show collections view"""
        self.collections_dock.setHidden(not event)

    def showMetadatasView(self, event):
        """show dock JSON view"""
        self.metadatas_dock.setHidden(not event)

    def showThumbView(self, event):
        """show dock thumbnail view"""
        self.thumbnail_dock.setHidden(not event)

    def showMapView(self, event):
        """show dock map view"""
        self.map_dock.setHidden(not event)

    def showLogView(self, event):
        """show dock log view"""
        self.log_dock.setHidden(not event)

    def showHidePhotoList(self, event):
        """show/hide photo list"""
        self.mdiPhotosList.setHidden(not event)

    def showHidePhotoThumb(self, event):
        """show/hide photo thumb"""
        self.mdiPhotosThumb.setHidden(not event)

    def onShowThumbsInPhotosList(self, event):
        """show/hide thumbs in photos list"""
        self.photosListView.useThumbs(event and lr_api.has_id_column())

        settings.setValue("thumbInPhotosList", event)

    ##############################################################
    #
    # Methods for Open Catalog
    #
    ##############################################################

    def openLrCatalog(self, filename, columns=None, criteria="videos=0"):
        """
        Open Lightroom catalog
        """
        log.info("openLrCatalog %s", filename)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        lr_api.open(filename)
        if not lr_api.is_connected():
            self.statusBar().showMessage(
                f'Failed to open Lightroom catalog "{filename}" : ({lr_api.exception})'
            )
            # clear UI
            self.setWindowTitle("Lightroom Viewer")
            self.collectionsView.setModel(CollectionsModel())
            self.photosListView.model().modelReset.emit()
            self.addressBar.setText("")
            self.label_photos_count.setText(
                STATUS_LABEL_COUNT.format(lr_api.query_count())
            )
            QApplication.restoreOverrideCursor()
            return False

        # prepare access to image for this catalog
        thumbs_provider.open_provider(filename)
        self.actionThumbsInPhotoList.setEnabled(thumbs_provider.has_thumbs)
        self.actionThumbsInPhotoList.setChecked(thumbs_provider.has_thumbs)
        self.btPhotosThumb.setEnabled(thumbs_provider.has_thumbs)
        self.photosListView.useThumbs(thumbs_provider.has_thumbs)
        if not thumbs_provider.has_thumbs:
            self.btPhotosList.setChecked(True)
            # change view done after lr_api.query for avoid bad lr_id

        # clone lr_api connection for access to photo metadatas (access when onPhotoRowChanged)
        self.photo_metadatas.clone_connection(lr_api)

        self.setWindowTitle(f"Lightroom Viewer - {lr_api.lrcat_file}")
        self.addRecentCatalog(filename)

        model = CollectionsModel()
        self.collectionsView.setModel(model)
        model.populate()
        self.collectionsView.expand_siblings()

        # add last query file to collections tree
        query_file = settings.value("LastQueryFile", "")
        if query_file:
            self.collectionsView.loadQueries(query_file, False)

        lr_api.query(criteria, columns)
        if not thumbs_provider.has_thumbs:
            # time for change view
            self.changeView("list")
            self.mdiPhotosThumb.setHidden(True)
        self.updateAfterQuery()

        url = f"{ROOT_QUERY}{lr_api.criteria()}?{lr_api.columns()}"
        self.addressBar.setText(url)
        QApplication.restoreOverrideCursor()
        return True

    def openLrCatalogDlg(self):
        """
        Dialog open Lightroom catalog
        """
        if not self.lastChanceToSaveQueries():
            return
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Lightroom catalog",
            "",
            "Lightroom Files (*.lrcat);;All files (*.*)",
        )
        if not filename:
            return
        self.openLrCatalog(filename)

    ##############################################################
    #
    # Methods for manage Recent Catalogs menu
    #
    ##############################################################

    def onRecentCatalog(self, action):
        """
        open recent file from menu
        """
        if not self.lastChanceToSaveQueries():
            return
        self.openLrCatalog(action.text())

    def addRecentCatalog(self, filename):
        """
        add new catalog to menu

        # TODO bug when self.recentFiles is empty (!?) : no visible

        """
        # remove filename from menu if exists (for move)
        for action in self.recentCatalogsMenu.actions():
            if action.text() == filename:
                self.recentCatalogsMenu.removeAction(action)
                break
        # insert menu
        action = QAction(filename, self)
        actions = self.recentCatalogsMenu.actions()
        before_action = actions[0] if actions else None
        self.recentCatalogsMenu.insertAction(before_action, action)
        # limit catalogs number : remove last catalog
        if len(self.recentCatalogsMenu.actions()) > settings.value(
            "MaxRecentCatalog", 10
        ):
            action = self.recentCatalogsMenu.actions()[-1]
            self.recentCatalogsMenu.removeAction(action)

    def restoreRecentCatalogs(self):
        """
        build recent catalogs menu from settings
        """
        filenames = settings.value("recentFiles", [])
        for filename in filenames:
            self.addRecentCatalog(filename)

    def saveRecentCatalogs(self):
        """
        save recent catalogs menu to settings
        """
        recentfiles = []
        for action in self.recentCatalogsMenu.actions()[::-1]:
            recentfiles.append(action.text())
        settings.setValue("recentFiles", recentfiles)

    def recentCatalog(self) -> str:
        """
        return last catalog opened
        """
        actions = self.recentCatalogsMenu.actions()
        if not actions:
            return None
        return actions[0].text()

    ##############################################################
    #
    # Methods querying Lightroom catalog
    #
    ##############################################################

    def onSelectCollection(self, index: QModelIndex):
        """
        Lightroom select collection from tree collection
        """
        item = index.internalPointer()
        self.selectCollection(item)

    def onQueryUnstored(self, criteria: str, columns: str):
        """
        query unstored from tree collection to be executed
        """
        url = f"{ROOT_QUERY}{criteria}?{columns}"
        self.addressBar.setText(url)
        self.onURL()

    def selectCollection(self, item: TreeItem, sort_column=""):
        """
        select collection (Lightroom Collections, Folders, Keywords, lrtools Queries ).
          item : a LrModelCollections.TreeItem
          crit : criteria to add (typically sort column)
        """
        path_setcoll = item.absolutePath()
        item_type = item.itemType()
        id_lr = item.userData()
        sort = (
            f",sort={sort_column}" if sort_column else f",sort={lr_api.sort_column()}"
        )
        log.info(
            'onSelectCollection: type=%s idlr:%s pseudo path="%s"',
            item_type,
            id_lr,
            path_setcoll,
        )

        if item_type in [
            ItemType.COLLECTION_GROUP,
            ItemType.LRTOOLS_COLLECTION_QUERY,
            ItemType.LRTOOLS_QUERY_ROOT,
            ItemType.PUBLISH_SERVICE,
            ItemType.PUBLISH_COLLECTION_GROUP,
        ]:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        if item_type == ItemType.KEYWORD:
            lr_api.query(f"idkeyword={id_lr}{sort}")

        elif item_type == ItemType.COLLECTION_REGULAR:
            lr_api.query(f"idcollection={id_lr}{sort}")

        elif item_type == ItemType.COLLECTION_SMART:
            lr_api.smart_query(
                id_lr, sort_column if sort_column else lr_api.sort_column()
            )

        elif item_type in [
            ItemType.PUBLISH_COLLECTION,
            ItemType.PUBLISH_COLLECTION_BUILTIN,
        ]:
            lr_api.query(f"idpubcollection={id_lr}{sort}")

        elif item_type == ItemType.FOLDER:
            lr_api.query(f"idfolder={id_lr}{sort}")

        elif item_type == ItemType.LRTOOLS_QUERY:
            query, columns = id_lr
            lr_api.query(query, columns)

        else:
            assert False

        QApplication.restoreOverrideCursor()

        if lr_api.exception:
            # reset model before any dialog (update during dialog)
            self.photosListView.model().modelReset.emit()
            self.photosThumbView.model().modelReset.emit()
            QMessageBox.critical(self, "Error", f"Query failed: {lr_api.exception}")
            self.updateAfterQuery()
            return

        # select collection in treeview
        index = self.collectionsView.indexFromPath(path_setcoll)
        self.collectionsView.selectionModel().clearSelection()
        self.collectionsView.selectionModel().select(
            index, QItemSelectionModel.SelectionFlag.Select
        )

        # update address bar
        if item_type == ItemType.LRTOOLS_QUERY:
            self.addressBar.setText(
                f"Query:/{lr_api.criteria()}?{lr_api.columns(visible_col=True)}"
            )
        else:
            self.addressBar.setText(
                f"{path_setcoll}/sort={lr_api.sort_column()}?{lr_api.columns(visible_col=True)}"
            )

        self.updateAfterQuery()

    def onSearch(self):
        """Enter in search bar"""
        searchText = self.searchField.text()
        searchWhere = self.searchWhere.currentText()
        log.info("OnSearch '%s' in '%s", searchText, searchWhere)
        self.selectSearch(searchWhere, searchText)

    def selectSearch(self, where: str, text: str):
        """search something somewhere"""
        log.info("Search '%s' in '%s", text, where)
        lwhere = where.lower()

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        if lwhere == WHERE_SEARCH.ANY.value.lower():
            lua = {
                0: {
                    "criteria": "all",
                    "operation": "all",
                    "value": text,
                    "value2": "",
                },
                "combine": "intersect",
            }
            lr_api.query_smart_data(lua)

        elif lwhere == WHERE_SEARCH.FILENAME.value.lower():
            lr_api.query(f"name=%{text}%")

        # elif lwhere == str(WHERE_SEARCH.FILECOPY):
        #     lr_api.query(f"name={text}")

        elif lwhere == WHERE_SEARCH.TITLE.value.lower():
            lr_api.query(f"title=%{text}%")

        elif lwhere == WHERE_SEARCH.CAPTION.value.lower():
            lr_api.query(f"caption=%{text}%")

        # elif lwhere == WHERE_SEARCH.META_ANY.value.lower():
        #     log.info("search %s unsupported")
        #     return

        elif lwhere == WHERE_SEARCH.META_EXIF.value.lower():
            lua = {
                0: {
                    "criteria": "exif",
                    "operation": "any",
                    "value": text,
                    "value2": "",
                },
                "combine": "intersect",
            }
            lr_api.query_smart_data(lua)

        elif lwhere == WHERE_SEARCH.META_IPTC.value.lower():
            lua = {
                0: {
                    "criteria": "iptc",
                    "operation": "any",
                    "value": text,
                    "value2": "",
                },
                "combine": "intersect",
            }
            lr_api.query_smart_data(lua)

        else:
            assert False

        QApplication.restoreOverrideCursor()

        if lr_api.exception:
            # reset model before any dialog (update during dialog)
            self.photosListView.model().modelReset.emit()
            self.photosThumbView.model().modelReset.emit()
            QMessageBox.critical(self, "Error", f"Query failed: {lr_api.exception}")
            self.updateAfterQuery()
            return

        # update address bar
        search_type = WHERE_SEARCH(where).name.capitalize()
        self.addressBar.setText(
            f"Search:/{search_type}/{text}?{lr_api.columns(visible_col=True)}"
        )

        self.updateAfterQuery()

    def onUrlActivated(self, index):
        """select URL from combo"""
        log.info("onUrlActivated index:%s", index)
        self.onURL()

    def onURL(self):
        """
        Lightroom select criteria from Enter in URL bar
        """
        query_url = self.addressBar.text()
        log.info('onURL: query="%s"', query_url)

        for section in [ROOT_FOLDER, ROOT_KEYWORD, ROOT_COLLECTION, ROOT_PUBCOLLECTION]:
            if query_url.startswith(section):
                sort_column = ""
                parts = query_url.split("/")
                if len(parts) == 1:
                    QMessageBox.critical(None, "Error", "Invalid collection")
                    return
                pos = parts[-1].find("?")
                if pos > 0:
                    criteria, columns = parts[-1].split("?")
                    dcrit = criteria_to_dict(criteria)
                    if "sort" in dcrit:
                        (sort_column,) = dcrit["sort"]
                    lr_api.prepare_query(criteria=criteria, columns=columns)
                    url = "/".join(parts[:-1])
                else:
                    url = "/".join(parts[:-1])

                item = self.collectionsView.pathToItem(url, case=False)
                if item is None:
                    QMessageBox.critical(None, "Error", "Invalid collection")
                    return

                self.selectCollection(item, sort_column)
                return

        if query_url.startswith(ROOT_SEARCH):
            pos = query_url.find("?")
            if pos > 0:
                columns = query_url[pos + 1 :]
                lr_api.prepare_query(columns=columns)
                url = query_url[:pos]
            else:
                columns = "name,datecapt,iso"
                url = query_url
            parts = url.split("/")
            if len(parts) < 3:
                QMessageBox.critical(None, "Error", "Invalid Syntax")
                return
            self.selectSearch(parts[1], parts[2])
            return

        if not query_url.startswith(ROOT_QUERY):
            QMessageBox.critical(None, "Error", "Invalid root URL")
            log.error("Invalid root URL")
            return

        query = query_url[len(ROOT_QUERY) :]
        parts = query.split("?", 1)
        if len(parts) != 2:
            QMessageBox.critical(None, "Error", "Invalid syntax")
            return
        criteria, columns = parts
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        lr_api.query(criteria, columns)
        QApplication.restoreOverrideCursor()
        if lr_api.exception:
            QMessageBox.critical(self, "Error", f"Query failed: {lr_api.exception}")

        self.collectionsView.clearSelection()

        self.updateAfterQuery()

    def navigateForward(self):
        """navigate next folder in history"""
        url = self.addressBar.forward()
        log.info("navigate forward %s", url)
        if url:
            self.onURL()

    def navigateBack(self):
        """navigate previous folder in history"""
        url = self.addressBar.back()
        log.info("navigate back: %s", url)
        if url:
            self.onURL()

    def queryAll(self):
        """query all photos and videes"""
        lr_api.query(criteria="")
        self.updateAfterQuery()

    def queryAllPhotos(self):
        """query all photos and videes"""
        lr_api.query(criteria="videos=0")
        self.updateAfterQuery()

    ##############################################################
    #
    # Methods for query actions
    #
    ##############################################################

    def onCreateQuery(self, _):
        """create query"""
        self.collectionsView.createQuery()

    def onRenameQuery(self, _):
        """rename active query"""
        self.collectionsView.renameQuery()

    def onRemoveQuery(self, _):
        """remove active query"""
        self.collectionsView.removeQuery()

    def onCreateQueryCollection(self, _):
        """crea&e query collection"""
        self.collectionsView.createQueryCollection()

    def onLoadQueries(self, _, merge=False):
        """load queries (merge)"""
        if not self.lastChanceToSaveQueries():
            return
        self.collectionsView.onLoadQueries(None, merge)

    def lastChanceToSaveQueries(self):
        """last chance to save queries"""
        if self.collectionsView.isQueriesModified():
            ret = QMessageBox.question(
                self,
                "Queries modified",
                "Do you want save queries ?",
                buttons=QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
            )
            if ret == QMessageBox.StandardButton.Yes:
                self.collectionsView.onSaveQueries(True)
                return True
            if ret == QMessageBox.StandardButton.No:
                return True
            # cancel
            return False
        return True

    ##############################################################
    #
    # Methods for map actions
    #
    ##############################################################

    def onSetMapType(self, map_type):
        """set map type (tiles)"""
        self.mapWidget.setMapType(map_type, self.actionMapCluster.isChecked())
        settings.setValue("mapTiles", map_type)

    def onShowQueryLocations(self):
        """show GPS locations on map for results of current query"""
        # check GPS columns
        if not self._check_add_gps_columns():
            # columns not presents, not added
            return
        col_lat = lr_api.column_index("latitude")
        col_lon = lr_api.column_index("longitude")
        map_loc = set()
        locations = []
        loc_null = 0
        loc_dup = 0
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        for row in range(0, lr_api.query_count()):
            # photo_id = lr_api.get_lr_id(row)
            latitude = lr_api.query_results[row][col_lat]
            longitude = lr_api.query_results[row][col_lon]
            if latitude is None or longitude is None:
                loc_null += 1
                continue
            location = (latitude, longitude)
            if location in map_loc:
                loc_dup += 1
                # continue
            map_loc.add(location)
            locations.append((row, location))
        log.info(
            "display %s locations (unset:%s, duplicated:%s)",
            len(locations),
            loc_null,
            loc_dup,
        )
        self.mapWidget.set_locations(locations)
        QApplication.restoreOverrideCursor()

        # photos rows list
        rows = [row for row, _ in locations]
        # clear current selection
        win = self.activeMainWindow()
        win.selectionModel().clearSelection()
        # select all rows
        selection = QItemSelection()
        for num, row in enumerate(rows):
            index = win.model().index(row, 0)
            selection.append(QItemSelectionRange(index))
            if num == 0:
                win.selectionModel().setCurrentIndex(
                    index, QItemSelectionModel.SelectionFlag.Rows
                )
                win.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
        win.selectionModel().select(
            selection,
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )

    def onShowSelectedLocations(self):
        """show GPS locations on map for current selection"""
        # TODO save current selection before _check_add_gps_columns, then restore it
        # check GPS columns
        if not self._check_add_gps_columns():
            # columns not presents, not added
            return
        map_loc = set()
        locations = []
        loc_null = 0
        loc_dup = 0
        col_lat = lr_api.column_index("latitude")
        col_lon = lr_api.column_index("longitude")
        win = self.activeMainWindow()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        for index in win.selectionModel().selection().indexes():
            row = index.row()
            latitude = lr_api.query_results[row][col_lat]
            longitude = lr_api.query_results[row][col_lon]
            if latitude is None or longitude is None:
                loc_null += 1
                continue
            location = (latitude, longitude)
            if location in map_loc:
                loc_dup += 1
                # continue
            map_loc.add(location)
            locations.append((row, location))
        log.info(
            "display %s locations (unset:%s, duplicated:%s)",
            len(locations),
            loc_null,
            loc_dup,
        )
        self.mapWidget.set_locations(locations)
        QApplication.restoreOverrideCursor()

    def onSelectedVisiblePhotos(self):
        """select visible photos on map (from map bounds)"""
        # check GPS columns
        if not self._check_add_gps_columns():
            # columns not presents, not added
            return
        bounds = self.mapWidget.get_map_bounds()
        if bounds is None:
            return
        log.info("Bounds: %s", bounds)
        dcriteria = criteria_to_dict(lr_api.criteria())
        # fmt:off   <- avoid black crash
        dcriteria["gps"] = [
            f"{bounds["_northEast"]["lat"]:.4f};{bounds["_northEast"]["lng"]:.4f}/{bounds["_southWest"]["lat"]:.4f};{bounds["_southWest"]["lng"]:.4f}"
        ]
        # fmt: on
        criteria = dict_to_criteria(dcriteria)
        # print(bounds)
        url = f"{ROOT_QUERY}{criteria}?{lr_api.columns(True)}"
        self.addressBar.setText(url)
        self.onURL()
        print(QGuiApplication.queryKeyboardModifiers())
        # in addition ...
        if (
            QGuiApplication.queryKeyboardModifiers()
            == Qt.KeyboardModifier.ControlModifier
        ):
            self.onShowQueryLocations()

    def _check_add_gps_columns(self) -> bool:
        """check if query has GPS locations, add columns"""
        # update avec lrid_from_index
        col_latitude = lr_api.column_index("latitude")
        col_longitude = lr_api.column_index("longitude")
        if col_latitude == -1 or col_longitude == -1:
            ret = QMessageBox.question(
                self,
                "Add location column",
                "Currrent query has no Latitude, Longitude columns.\n\nAdd it and continue ?",
            )
            if ret == QMessageBox.StandardButton.No:
                return False
            columns = lr_api.columns()
            columns += ",latitude,longitude"
            lr_api.query(columns=columns)
            self.updateAfterQuery(setSort=False, setFirst=False)
            col_latitude = lr_api.column_index("latitude")
            col_longitude = lr_api.column_index("longitude")
        return True

    def onMapMarker(self, rows: list):
        """signal from map

        markers idphoto are rows in current query
        """
        log.info("Marker click row %s", rows)
        win = self.activeMainWindow()

        # select all rows
        selection = QItemSelection()
        for num, row in enumerate(rows):
            index = win.model().index(row, 0)
            selection.append(QItemSelectionRange(index))
            if num == 0:
                win.selectionModel().setCurrentIndex(
                    index, QItemSelectionModel.SelectionFlag.Clear
                )
                win.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
        win.selectionModel().select(
            selection,
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows,
        )

    def setUseMarkerCluster(self, checked):
        """use cluster of markers"""
        self.mapWidget.setMapType(self.mapWidget.getMapType(), use_cluster=checked)

    ##############################################################
    #
    # Methods various
    #
    ##############################################################

    def photosContextItemMenu(self, _):
        """create context menu for photos view"""
        menu = QMenu()
        self.updateEditMenu()
        self.updateSlideshowMenu()
        menu.addAction(self.actionStartSlideshow)
        menu.addAction(self.actionContinueSlideShow)
        menu.addSeparator()
        menu.addAction(self.actionThumbsInPhotoList)
        menu.addSeparator()
        action = QAction("Resize columns to window", self)
        action.triggered.connect(self.onPhotoViewResize2Win)
        menu.addAction(action)
        action = QAction("Resize columns to contents", self)
        action.triggered.connect(self.onPhotoViewResize2Contents)
        menu.addAction(action)
        menu.exec(QCursor.pos())

    def setphotosViewIndex(self, location):
        """
        Set photo thumbnail, metadatas, gps location for various views. Location in ["first", "prev", "next", "current"]

        Source index is taken from active MDI window or last MDI window activated
        Real work is done in onPhotoRowChanged, called via rowchanged signal after setCurrent index

        """
        win = self.activeMainWindow()
        if win is None:
            log.info("no active main window")
            return

        if location == "first":
            index = win.model().index(0, 0)
            if not index.isValid():
                log.info("window empty")
                self.onPhotoRowChanged(index)
                return
            win.selectionModel().setCurrentIndex(
                index,
                QItemSelectionModel.SelectionFlag.SelectCurrent
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            return

        curIndex = win.currentIndex()
        if not curIndex.isValid():
            log.info("No current index")
            return
        if location == "prev":
            index = curIndex.model().index(
                (curIndex.row() - 1) % curIndex.model().rowCount(curIndex.parent()),
                0,
                curIndex.parent(),
            )

        elif location == "next":
            index = curIndex.model().index(
                (curIndex.row() + 1) % curIndex.model().rowCount(curIndex.parent()),
                0,
                curIndex.parent(),
            )

        elif location == "current":
            # need change row for generate signal TODO
            self.onPhotoRowChanged(curIndex)
            return
        else:
            assert False

        # win.setCurrentIndex(index)
        win.selectionModel().setCurrentIndex(
            index,
            QItemSelectionModel.SelectionFlag.SelectCurrent
            | QItemSelectionModel.SelectionFlag.Rows,
        )

    def onSelectionChanged(self, selected: QItemSelection, deselected: QItemSelection):
        """signal selection changed in photosView"""
        log.info(
            "onSelectionChanged selected:%s, deselect:%s",
            selected.count(),
            deselected.count(),
        )
        selectedCount = len(
            [
                index
                for index in self.photosListView.selectionModel().selectedIndexes()
                if index.column() == 0
            ]
        )
        self.label_photos_selected.setText(STATUS_LABEL_SELECTED.format(selectedCount))

    def onPhotoRowChanged(self, index: QModelIndex):
        """selection changed in main explorer"""
        if not index.isValid():
            self.thumbnailWidget.setImage(None)
            self.slideshow.setPhoto(None)
            self.metadatas_view.setMetadatas(None)
            self.mapWidget.hide_current_location()
            return
        log.info("onPhotoRowChanged: %s", index.row())
        lr_id = self.lrid_from_index(index)
        # get metadatas
        self.photo_metadatas.readMetadatas(lr_id)

        # get thumb and image
        thumb = thumbs_provider.get_thumb(lr_id)
        self.thumbnailWidget.setImage(thumb)
        if self.slideshow.isVisible():
            # Warning : slideshow optimization : image not set when invisible
            photo = thumbs_provider.get_thumb(lr_id, "max")
            self.slideshow.setPhoto(photo)

        self.metadatas_view.setMetadatas(self.photo_metadatas)
        self.mapWidget.set_location(
            self.photo_metadatas.gps_location(),
            index.row(),
            self.actionMapFlyto.isChecked(),
        )

    def onPhotoDoubleClicked(self, index: QModelIndex):
        """doubleclick in photoview : active slideshow in fullscreen, display photo"""
        self.slideshow_dock.setHidden(False)
        self.stateSlideshowFloating = self.slideshow_dock.isFloating()
        if not self.stateSlideshowFloating:
            log.info("setFloating True")
            self.slideshow_dock.setFloating(True)
        log.info("Enter fullscreen")
        self.slideshow_dock.showFullScreen()

        lr_id = self.lrid_from_index(index)
        photo = thumbs_provider.get_thumb(lr_id, "max")
        self.slideshow.setPhoto(photo)

    def onPhotoViewResize2Contents(self):
        """resize columns of photo list view to contents"""
        self.photosListView.resizeColumnsToContents()

    def onPhotoViewResize2Win(self):
        """resize columns of photo list view to fit in window"""
        self.photosListView.resizeColumnsToWindow(True)

    def selectColumns(self):
        """dialog columns selection"""
        dialog = ColumnsDialog(lr_api.columns(True), self)
        if not dialog.exec():
            return
        parts = self.addressBar.text().split("?")
        parts[-1] = dialog.ui.columns_result.text()
        url = "?".join(parts)
        self.addressBar.setText(url)
        self.onURL()

    def selectCriterias(self):
        """dialog criterias selection"""
        dialog = CriteriaDialog(lr_api.criteria(), self)
        if not dialog.exec():
            return
        parts = self.addressBar.text().split(":/", maxsplit=1)
        parts = parts[1].split("?", maxsplit=1)
        parts[0] = dialog.ui.criteria_result.text()
        # scheme always changed to a "Query:/"
        url = f"{ROOT_QUERY}{"?".join(parts)}"
        self.addressBar.setText(url)
        self.onURL()

    def selectDefaultColumns(self):
        """choose default columns"""
        dialog = ColumnsDialog(lr_api.columns(True), self)
        if not dialog.exec():
            return
        settings.setValue("defaultColumns", dialog.ui.columns_result.text())
        lr_api.default_columns = dialog.ui.columns_result.text()

    ##############################################################
    #
    # Methods about sorting
    #
    ##############################################################

    def setSortIndicator(self, sort_index, sort_order):
        """local setSortIndicator : avoid onSortIndicatorChanged"""
        self.photosListView.horizontalHeader().sortIndicatorChanged.disconnect(
            self.onSortIndicatorChanged
        )
        self.photosListView.horizontalHeader().setSortIndicator(sort_index, sort_order)
        self.photosListView.horizontalHeader().sortIndicatorChanged.connect(
            self.onSortIndicatorChanged
        )

    def onSortIndicatorChanged(self, index, order):
        """
        order changed in photos table header
        """
        log.info("onSortIndicatorChanged - index=%s order=%s", index, order)

        # save current selection
        win = self.activeMainWindow()
        col_id = lr_api.column_index("id")
        if col_id != -1:
            ids_sel = [
                lr_api.query_results[index_sel.row()][col_id]
                for index_sel in win.selectionModel().selectedRows()
            ]

        column_name = self.photosListView.columnName(index)
        lr_api.query_sort(column_name, order == Qt.SortOrder.AscendingOrder)

        # update address
        url = self.addressBar.text()
        if url.startswith(ROOT_QUERY):
            self.addressBar.setText(
                f"{ROOT_QUERY}{lr_api.criteria()}?{lr_api.columns(visible_col=True)}"
            )
        else:
            parts = url.split("/")
            _, cols = parts[-1].split("?")
            self.addressBar.setText(
                f"{"/".join(parts[:-1])}/sort={lr_api.sort_column()}?{cols}"
            )

        self.updateAfterQuery(setSort=False)

        # restore selection
        if col_id != -1:
            selection = QItemSelection()
            for lr_id in ids_sel:
                for row in range(0, lr_api.query_count()):
                    if lr_api.query_results[row][col_id] == lr_id:
                        selection.append(
                            QItemSelectionRange(self.photoModel.index(row, 0))
                        )
                        break
            win.selectionModel().select(
                selection,
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
            if selection.count() > 0:
                index_sel = selection.indexes()[0]
                win.setCurrentIndex(index_sel)
                win.scrollTo(index_sel, QAbstractItemView.ScrollHint.PositionAtCenter)
                self.setphotosViewIndex("current")

    ##############################################################
    #
    # Methods for slideshow
    #
    ##############################################################

    def createSlideshowWidget(self):
        """create slideshow window"""
        slideshow = SlideShow()
        slideshow.setTimerEnabled(False)
        slideshow.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        slideshow.customContextMenuRequested.connect(self.slideshowContextItemMenu)
        slideshow.previous.connect(self.onPrevSlide)
        slideshow.next.connect(self.onNextSlide)
        slideshow.doubleClicked.connect(self.toggleSlideshowFullScreen)
        slideshow.setInterval(settings.value("slideShowDelay", 5000))
        return slideshow

    def slideshowContextItemMenu(self):
        """context menu for slideshow"""
        self.updateSlideshowMenu()
        menu = QMenu()
        menu.addAction(self.actionStartSlideshow)
        menu.addAction(self.actionContinueSlideShow)
        menu.addAction(self.actionPauseSlideshow)
        menu.addSeparator()
        menu.addAction(self.actionSlideshowFullscreen)
        action = QAction("Hide Slideshow", self)
        action.triggered.connect(lambda close: self.slideshow_dock.hide())
        menu.addAction(action)
        action = QAction("Dock Slideshow", self)
        action.triggered.connect(lambda dock: self.slideshow_dock.setFloating(False))
        menu.addAction(action)
        menu.exec(QCursor.pos())

    def toggleSlideshowFullScreen(self):
        """slideshow widget in fullscreen"""
        if self.slideshow_dock.isFullScreen():
            log.info("exit from fullscreen")
            self.show()
            self.slideshow_dock.showNormal()
            if not self.stateSlideshowFloating:
                log.info("setFloating False")
                self.slideshow_dock.setFloating(False)
        else:
            self.stateSlideshowFloating = self.slideshow_dock.isFloating()
            if not self.stateSlideshowFloating:
                log.info("setFloating True")
                self.slideshow_dock.setFloating(True)
            log.info("Enter fullscreen")
            if not self.slideshow_dock.isVisible():
                self.showSlideshowView(True)
            self.slideshow_dock.showFullScreen()

    def onStartSlideshow(self):
        """ "Start slideshow from first photo"""
        self.updateToolbar()
        self.setphotosViewIndex("first")
        self.showSlideshowView(True)
        self.slideshow.setTimerEnabled(True)

    def onContinueSlideshow(self):
        """ "Start or continue slideshow from current photo"""
        self.updateToolbar()
        self.setphotosViewIndex("current")
        self.showSlideshowView(True)
        self.slideshow.setTimerEnabled(True)

    def onPauseSlideshow(self):
        """Stop r pause slideshow of current folder"""
        self.slideshow.setTimerEnabled(False)

    def onPrevSlide(self):
        """click button prev in slideshow"""
        self.setphotosViewIndex("prev")

    def onNextSlide(self):
        """click button next in slideshow"""
        log.info("onNextSlide")
        self.setphotosViewIndex("next")

    def onSetSlideshowSpeed(self, speed):
        """set slideshow speed"""
        value = speed * 1000
        self.slideshow.setInterval(value)
        settings.setValue("slideShowDelay", value)

    ##############################################################
    #
    # Methods internal
    #
    ##############################################################

    def lrid_from_index(self, index: QModelIndex) -> int:
        """return lightroom photo index from QModelIndex"""
        col_id = lr_api.column_index("id")
        if col_id == -1:
            log.info("no 'id' column")
            return None
        return lr_api.query_results[index.row()][col_id]

    def activeMainWindow(self) -> QAbstractItemView:
        """
        return current active MDI window or last MDI window activated
        """
        win = self.mdi.activeSubWindow()
        if win:
            win = self.mdi.activeSubWindow().widget()
            self.lastSubWindowActived = win
        else:
            if self.lastSubWindowActived is None:
                return None
            win = self.lastSubWindowActived
        return win


def main():
    """
    main console, get arguments, create application
    """

    # build command parser
    parser = argparse.ArgumentParser(
        description="View Photos from Lightroom catalog",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("columns", help="Initial columns to display", nargs="?")
    parser.add_argument(
        "criteria",
        help='Initial criteria (for syntax: see project "Lightroom-SQL-tools" on github)',
        nargs="?",
    )
    default_lrcat = (
        settings.value("recentFiles", [])[-1]
        if settings.value("recentFiles", [])
        else lr_api.lrconfig.default_lrcat
    )
    parser.add_argument(
        "-b",
        "--lrcat",
        default=default_lrcat,
        help='Ligthroom catalog file for database request (default:"%(default)s")',
    )
    parser.add_argument(
        "-S", "--slideshow", action="store_true", help="Start slideshow in fullscreen"
    )
    parser.add_argument(
        "-t",
        "--timer",
        type=int,
        default=5,
        help="Seconds between slide (used with --slideshow option)",
    )
    parser.add_argument(
        "-D",
        "--dark-theme",
        choices=["dark", "light", "qdark", "none"],
        default="qdark",
        help="Theme to use",
    )
    parser.add_argument(
        "-V", "--version", action="store_true", help="Show version and exit"
    )

    args = parser.parse_args()

    if args.version:
        print(f"{APP_NAME} - Version {APP_VERSION}")
        print(f"using lrtools version : {LRTOOLS_VERSION}")
        sys.exit()

    app = QApplication(sys.argv)
    # Apply theme
    if args.dark_theme:
        if args.dark_theme == "dark":
            QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Dark)
        elif args.dark_theme == "light":
            QGuiApplication.styleHints().setColorScheme(Qt.ColorScheme.Light)
        elif args.dark_theme == "qdark":
            qdarktheme.setup_theme("dark")

    App(args)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
