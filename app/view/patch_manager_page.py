from PySide6.QtCore import QModelIndex, Qt, QObject, QEvent, Signal, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPixmap, QPen, QIcon
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QTableWidgetItem, QHeaderView, QStyle,QFrame, QLabel
from PySide6.QtWebEngineWidgets import QWebEngineView

from pyecharts.charts import Radar, Pie
from pyecharts import options as opts

import os
import shutil
import sys
from difflib import SequenceMatcher

from qfluentwidgets import ScrollArea,  ImageLabel, StateToolTip, TableWidget, LineEdit, PrimaryToolButton
from qfluentwidgets import FluentIcon as FIF
from ..common.config import cfg, HELP_URL, REPO_URL, EXAMPLE_URL, FEEDBACK_URL
from ..common.icon import Icon, FluentIconBase
from ..common.style_sheet import StyleSheet
from ..common.signal_bus import signalBus


    


class PatchTable(TableWidget):

    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.__initWidget()

    def __initWidget(self):

        self.setObjectName('patchTable')
        
        self.initTable()

    def initTable(self):

        self.setColumnCount(6)
        self.setRowCount(0)
        self.setBorderRadius(8)
        self.setBorderVisible(True)
        
        self.verticalHeader().hide()
        self.setSortingEnabled(True)


        self.setHorizontalHeaderLabels([
            self.tr('Index'), self.tr('Preview'), self.tr('Name'), self.tr('Time'), self.tr('Max Strength'), self.tr('Effect')
        ])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        initinfos = [
            {
                'patch_preview': ':/gallery/images/patches/advpatch1_50.png',
                'patch_name': self.tr('Generic Patch')+'1',
                'patch_time': '-',
                'patch_strength': '100%',
                'patch_effect': '-'
            },
            {
                'patch_preview': ':/gallery/images/patches/advpatch2_50.png',
                'patch_name': self.tr('Generic Patch')+'2',
                'patch_time': '-',
                'patch_strength': '100%',
                'patch_effect': '-'
            },
            {
                'patch_preview': ':/gallery/images/patches/advpatch3_50.png',
                'patch_name': self.tr('Generic Patch')+'3',
                'patch_time': '-',
                'patch_strength': '100%',
                'patch_effect': '-'
            },
        ]

        for i, patch_info in enumerate(initinfos):
            self.add_patch(patch_info)

    def add_patch(self, patch_info):
        
        row = self.rowCount()
        self.setRowCount(row + 1)

        item = QTableWidgetItem(str(row + 1))
        item.setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 0, item)
        
   
        previewItem = QWidget()  
        previewItemLayout = QVBoxLayout()  
        previewItemLayout.setAlignment(Qt.AlignCenter)  
        previewItem.setLayout(previewItemLayout) 
        
        preview = ImageLabel() 
        preview.setPixmap(QPixmap(patch_info['patch_preview'])) 
        preview.setFixedSize(64, 64)  
        previewItemLayout.addWidget(preview)  
        
        self.setCellWidget(row, 1, previewItem)  

        name = QTableWidgetItem(patch_info['patch_name'])
        self.setItem(row, 2, name)
        self.item(row, 2).setTextAlignment(Qt.AlignCenter)

        self.setItem(row, 3, QTableWidgetItem(patch_info['patch_time']))
        self.item(row, 3).setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 4, QTableWidgetItem(patch_info['patch_strength']))
        self.item(row, 4).setTextAlignment(Qt.AlignCenter)
        self.setItem(row, 5, QTableWidgetItem(patch_info['patch_effect']))
        self.item(row, 5).setTextAlignment(Qt.AlignCenter)

        self.setRowHeight(row, 80)



class PatchManagerPage(ScrollArea):

    def __init__(self,parent=None, base_path = None):
        super().__init__(parent=parent)

        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        self.tableArea = PatchTable(self.view)

        self.trainArea = QFrame(self.view)
        self.trainAreaLayout = QHBoxLayout(self.trainArea)

        self.pathLabel = QLabel(self.tr('Select Train Dataset Directory'), self)
        self.pathedit = LineEdit(self)
        self.pathButton = PrimaryToolButton(FIF.FOLDER, self)
        self.trainButton = PrimaryToolButton(Icon.MODEL_TRAIN, self)

        self.__initWidget()
    
    def __initWidget(self):
        self.initLayout()
        self.view.setObjectName('view')
        self.setObjectName('patchManagerPage')
        StyleSheet.PATCH_MANAGER_PAGE.apply(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)

        self.pathedit.setFixedWidth(150)


        self.connectSignalToSlot()

    def connectSignalToSlot(self):

        pass

    def initLayout(self):
        
        self.vBoxLayout.addSpacing(20)
        self.vBoxLayout.addWidget(self.tableArea, 1, Qt.AlignTop)
        self.tableArea.setFixedHeight(500)
        self.vBoxLayout.addSpacing(20)
        self.vBoxLayout.addWidget(self.trainArea, 1, Qt.AlignHCenter|Qt.AlignTop)
        self.trainArea.setFixedHeight(100)
        self.trainAreaLayout.addWidget(self.pathLabel, 1, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.pathedit, 1, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.pathButton, 0, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.trainButton, 0, Qt.AlignCenter)

        self.trainArea.setFixedWidth(500)

        self.vBoxLayout.setContentsMargins(36, 0, 36, 0)

    

    