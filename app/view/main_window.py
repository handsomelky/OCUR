# coding: utf-8
from typing import List
from PySide6.QtCore import Qt, Signal, QEasingCurve, QUrl, QSize
from PySide6.QtGui import QIcon, QDesktopServices, QColor
from PySide6.QtWidgets import QApplication, QHBoxLayout, QFrame, QWidget



from qfluentwidgets import (NavigationAvatarWidget, NavigationItemPosition, MessageBox, FluentWindow,
                            SplashScreen, ScrollArea)
from qfluentwidgets import FluentIcon as FIF

from .home_page import HomePage
from .patch_all_page import PatchAllPage
from .patch_part_page import PatchPartPage
from .patch_manager_page import PatchManagerPage
from .setting_interface import SettingInterface
from ..common.config import  cfg
from ..common.icon import Icon
from ..common.signal_bus import signalBus
from ..common.translator import Translator
from ..common import resource

class MainWindow(FluentWindow):

    def __init__(self, mode, image_paths, base_path):
        super().__init__()
        self.initWindow()

        self.mode = mode
        self.image_paths = image_paths
        self.base_path = base_path

        # create sub interface
        self.homeInterface = HomePage(self)
        self.patchPartPage = PatchPartPage(self, base_path=base_path)
        self.patchAllPage = PatchAllPage(self, base_path=base_path)
        self.patchManagerPage = PatchManagerPage(self, base_path=base_path)

        self.settingInterface = SettingInterface(self)


        # enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)
        self.setCustomBackgroundColor(QColor(240, 244, 249), QColor(32, 32, 32))

        self.connectSignalToSlot()

        # add items to navigation interface
        self.initNavigation()

        self.handleMode()

        self.splashScreen.finish()

    def connectSignalToSlot(self):
        signalBus.micaEnableChanged.connect(self.setMicaEffectEnabled)
        signalBus.switchToSampleCard.connect(self.switchToSample)

    def handleMode(self):
        interfaces = self.findChildren(ScrollArea)
        if self.mode == 'mode1':
            self.stackedWidget.setCurrentWidget(self.patchPartPage, False)
            signalBus.initialImageSignal_part.emit(self.image_paths)
        elif self.mode == 'mode2':
            self.stackedWidget.setCurrentWidget(self.patchAllPage, False)
            signalBus.initialImageSignal_full.emit(self.image_paths)
        else:
            self.stackedWidget.setCurrentWidget(self.homeInterface, False)

        

    def initNavigation(self):
        # add navigation items
        t = Translator()
        self.addSubInterface(self.homeInterface, FIF.HOME, self.tr('Home'))
        self.addSubInterface(self.patchPartPage, Icon.MOSAIC, t.patchPart)
        self.addSubInterface(self.patchAllPage, Icon.TEXT_HIDE, t.patchAll)
        self.addSubInterface(self.patchManagerPage, Icon.PATCH_LIBRARY, t.patchManager)

        self.navigationInterface.addSeparator()

        # add custom widget to bottom

        self.addSubInterface(
            self.settingInterface, FIF.SETTING, self.tr('Settings'), NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(960, 780)
        self.setMinimumWidth(760)
        self.setWindowIcon(QIcon(':/gallery/images/logo.ico'))
        self.setWindowTitle('OCUR')

        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

        # create splash screen
        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(106, 106))
        self.splashScreen.raise_()

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()
        QApplication.processEvents()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, 'splashScreen'):
            self.splashScreen.resize(self.size())

    def switchToSample(self, routeKey):
        """ switch to sample """
        interfaces = self.findChildren(ScrollArea)
        for w in interfaces:
            if w.objectName() == routeKey:
                self.stackedWidget.setCurrentWidget(w, False)
