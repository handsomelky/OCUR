from PySide6.QtCore import QModelIndex, Qt, QObject, QEvent, Signal, QTimer, QSize, QAbstractItemModel
from PySide6.QtGui import QPainter, QColor, QPixmap, QPen, QIcon
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QTableWidgetItem, QHeaderView, QStyle,QFrame, QLabel, QFileDialog,QAbstractItemView
from PySide6.QtWebEngineWidgets import QWebEngineView

from pyecharts.charts import Radar, Pie
from pyecharts import options as opts

import os
import shutil
import sys
from difflib import SequenceMatcher

from qfluentwidgets import ScrollArea,  ImageLabel, StateToolTip, TableWidget, LineEdit, PrimaryToolButton,ComboBox
from qfluentwidgets import FluentIcon as FIF
from ..common.config import cfg, HELP_URL, REPO_URL, EXAMPLE_URL, FEEDBACK_URL
from ..common.icon import Icon, FluentIconBase
from ..common.style_sheet import StyleSheet
from ..common.signal_bus import signalBus

from ..utils.jsonTools import save_patch_info, load_patch_info

from ..api.train import TrainThread



class PatchTable(TableWidget):

    def __init__(self, parent=None, base_path = None):
        super().__init__(parent=parent)
        self.base_path = base_path
        self.patch_info_path = os.path.join(self.base_path, 'patches', 'patch.json')

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
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)


        self.setHorizontalHeaderLabels([
            self.tr('Index'), self.tr('Preview'), self.tr('Name'), self.tr('Time'), self.tr('Max Strength'), self.tr('Size')
        ])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        initinfos = load_patch_info(self.patch_info_path)["patches"]

        for patch_info in initinfos:
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
        time = QTableWidgetItem(patch_info['patch_time'])
        self.setItem(row, 3, time)
        self.item(row, 3).setTextAlignment(Qt.AlignCenter)
        strength = QTableWidgetItem(patch_info['patch_strength'])
        self.setItem(row, 4, strength)
        self.item(row, 4).setTextAlignment(Qt.AlignCenter)
        size = QTableWidgetItem(patch_info['patch_size'])
        self.setItem(row, 5, size)
        self.item(row, 5).setTextAlignment(Qt.AlignCenter)

        self.setRowHeight(row, 80)




class PatchManagerPage(ScrollArea):

    def __init__(self,parent=None, base_path = None):
        super().__init__(parent=parent)

        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        self.tableArea = PatchTable(self.view, base_path=base_path)

        self.trainArea = QFrame(self.view)
        self.trainAreaLayout = QHBoxLayout(self.trainArea)

        self.pathLabel = QLabel(self.tr('Select Train Dataset Directory'), self)
        self.pathEdit = LineEdit(self)
        self.pathButton = PrimaryToolButton(FIF.FOLDER, self)
        # 底纹尺寸选择
        self.patchNameLabel = QLabel(self.tr('Patch Name'), self)
        self.patchNameEdit = LineEdit(self)

        self.sizeLabel = QLabel(self.tr('Patch Size'), self)
        self.sizeButton = ComboBox(self)

        self.trainLabel = QLabel(self.tr('Generate Patch'), self)
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

        self.patchNameEdit.setFixedWidth(100)

        self.pathEdit.setFixedWidth(150)

        self.sizeButton.addItems([
            '20',
            '30',
            '50',
            '90'
        ])


        self.connectSignalToSlot()

    def connectSignalToSlot(self):

        self.pathButton.clicked.connect(self.selectTrainDataset)
        self.trainButton.clicked.connect(self.train)


    def initLayout(self):
        
        self.vBoxLayout.addSpacing(20)
        self.vBoxLayout.addWidget(self.tableArea, 1, Qt.AlignTop)
        self.tableArea.setFixedHeight(500)
        self.vBoxLayout.addSpacing(20)
        self.vBoxLayout.addWidget(self.trainArea, 1, Qt.AlignHCenter|Qt.AlignTop)
        self.trainArea.setFixedHeight(100)

        self.trainAreaLayout.addWidget(self.patchNameLabel, 1, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.patchNameEdit, 1, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.pathLabel, 1, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.pathEdit, 1, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.pathButton, 1, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.sizeLabel, 1, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.sizeButton, 1, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.trainLabel, 1, Qt.AlignCenter)
        self.trainAreaLayout.addWidget(self.trainButton, 1, Qt.AlignCenter)

        self.vBoxLayout.setContentsMargins(36, 0, 36, 0)

    def selectTrainDataset(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", "")
        if folder:
            self.pathEdit.setText(folder)
            self.base_path = folder

    def train(self):
        train_dataset_dir = self.pathEdit.text()
        size = int(self.sizeButton.currentText())
        self.thread = TrainThread(train_dataset_dir, size=size, base_path=self.base_path)
        self.thread.start()

        





    

    

    