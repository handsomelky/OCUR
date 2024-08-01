from decimal import Decimal
from PySide6.QtCore import QModelIndex, Qt, QObject, QEvent, Signal, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QPixmap, QPen, QIcon, QFont
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFileDialog, QFrame, QGraphicsView, QListWidgetItem, QLabel, QGraphicsPixmapItem, QGraphicsScene, QScrollArea, QCompleter
from PySide6.QtWebEngineWidgets import QWebEngineView
from ..utils.jsonTools import load_patch_info

from pyecharts.charts import Radar, Pie
from pyecharts import options as opts

import os
import shutil
import sys
from difflib import SequenceMatcher

from qfluentwidgets import ScrollArea,  TransparentToolButton, TransparentToggleToolButton, ListWidget, PushButton, SearchLineEdit, ComboBox, PrimaryPushButton, ProgressRing, LineEdit, ToggleButton, PrimaryToolButton, ScrollArea, CommandBar, ToolTipFilter, IconWidget, InfoBar, InfoBarPosition, ImageLabel, StateToolTip, MessageBoxBase, MessageBox, TextEdit
from qfluentwidgets import FluentIcon as FIF
from ..common.config import cfg, HELP_URL, REPO_URL, EXAMPLE_URL, FEEDBACK_URL
from ..common.icon import Icon, FluentIconBase
from ..common.style_sheet import StyleSheet
from ..common.signal_bus import signalBus

from ..api.patch import PatchThread
from ..api.evaluate import EvaluateThread




class ImageViewer(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene, self)
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)

        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.NoDrag)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)


        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        self.setLayout(layout)

        self.scale_factor = 1.0
        self.max_scale = 4  # 最大缩放级别
        self.min_scale = 0.4  # 最小缩放级别
        self.pixmap = None

    def load_image(self, file_path):
        if not self.pixmap:
            self.fit_to_view()
        self.pixmap = QPixmap(file_path)
        self.pixmap_item.setPixmap(self.pixmap)
        self.fit_to_view()


    def fit_to_view(self):
        self.view.setSceneRect(self.pixmap_item.boundingRect())  # 确保场景大小匹配图像大小
        self.view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def zoom_in(self):
        self.scale(1.25)

    def zoom_out(self):
        self.scale(0.8)

    def scale(self, factor):
        new_scale = self.scale_factor * factor
        if new_scale < self.min_scale or new_scale > self.max_scale:
            return
        self.scale_factor = new_scale
        self.view.scale(factor, factor)

    def set_drag_mode(self, enabled):
        if enabled:
            self.view.setDragMode(QGraphicsView.ScrollHandDrag)
        else:
            self.view.setDragMode(QGraphicsView.NoDrag)

class SearchBox(SearchLineEdit):
    """ Search Box """
    return_pressed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            if self.text()!='':#非空才触发信号，为空的时候触发了没意义。
                self.return_pressed.emit(self.text())
        super().keyPressEvent(event)


class InteractiveDropCover(QLabel):
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.base_path = base_path
        self.hover = False  # 鼠标悬停状态
        self.dropCoverLayout = QVBoxLayout()  # 使用 QVBoxLayout 来垂直堆叠图标和文字

        # 设置图标
        self.iconLabel = IconWidget(Icon.UPLOAD_IMAGE,self)
        self.iconLabel.setFixedSize(100, 100)
        self.iconLabel.setObjectName('iconLabel')

        # 设置文字
        textLabel = QLabel(self.tr('Click to upload an image or drag it here'))
        textLabel.setAlignment(Qt.AlignCenter)
        textLabel.setStyleSheet("font-size: 20px;")
        textLabel.setObjectName('textLabel')

        self.dropCoverLayout.addWidget(self.iconLabel,1,Qt.AlignCenter)
        self.dropCoverLayout.addWidget(textLabel,1,Qt.AlignCenter)
        self.setLayout(self.dropCoverLayout)


    def enterEvent(self, event):
        self.hover = True
        self.update()  # 触发重绘

    def leaveEvent(self, event):
        self.hover = False
        self.update()  # 触发重绘

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            uploads_dir = os.path.join(self.base_path, 'uploads')
            if os.path.exists(uploads_dir):
                shutil.rmtree(uploads_dir)  # 删除整个目录
            os.makedirs(uploads_dir)
            self.parent().load_file()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.hover :
            painter = QPainter(self)
            pen = QPen(QColor(0, 120, 215), 2, Qt.CustomDashLine)  # 设置虚线样式
            pen.setDashPattern([1, 3])  # 定义虚线模式（线长，间隔长）
            painter.setPen(pen)
            rect = self.rect().adjusted(10, 10, -10, -10)  # 留出边距
            painter.drawRoundedRect(rect, 10, 10)  # 绘制圆角矩形

class ProgressCover(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.progressCoverLayout = QVBoxLayout()  # 使用 QVBoxLayout 来垂直堆叠图标和文字

        self.progressRing = ProgressRing(self)
        self.progressRing.setTextVisible(True)
        self.progressRing.setFixedSize(160, 160)
        font = QFont()
        font.setPointSize(18) 
        self.progressRing.setFont(font)
        self.progressRing.setStrokeWidth(8)

        self.progressCoverLayout.addWidget(self.progressRing,0,Qt.AlignmentFlag.AlignCenter)
        self.setLayout(self.progressCoverLayout)
        self.hide()




class VisualizationArea(QWidget):
    patchProgressUpdated = Signal(int)
    barchartExpand = Signal(bool)
    ocrResultExpand = Signal(bool)
    updateChart = Signal(tuple)
    enableButtons = Signal()
    saveornot = Signal(bool)
    ocrResult = Signal(list)

    def __init__(self, parent=None, base_path=None):
        super().__init__(parent=parent)

        self.base_path = base_path

        self.fileNames = set()
        self.originalParent = None
        self.originalLayoutIndex = None
        self.patchedState = False
        self.alreadyPatched = False
        self.evaluatedState = False
        

        self.uploads_dir = os.path.join(base_path, 'uploads')
        self.patched_dir = os.path.join(base_path, 'results/patched_images')
        self.evaluated_upload_dir = os.path.join(base_path, 'results/evaluated_upload_images')
        self.evaluated_patched_dir = os.path.join(base_path, 'results/evaluated_patched_images')

        self.hBoxLayout = QHBoxLayout(self)
        self.picArea = QFrame(self)
        self.indexArea = QFrame(self)

        self.picLayout = QVBoxLayout(self.picArea)
        self.indexLayout = QVBoxLayout(self.indexArea)

        self.imageBar = CommandBar(self)
        

        self.viewer = ImageViewer(self.picArea)  # 使用自定义的图像查看器

        self.dargButton = TransparentToggleToolButton(FIF.MOVE, self.imageBar)
        self.zoomInButton = TransparentToolButton(FIF.ZOOM_IN, self.imageBar)
        self.zoomOutButton = TransparentToolButton(FIF.ZOOM_OUT, self.imageBar)
        self.leftButton = TransparentToolButton(FIF.PAGE_LEFT, self.imageBar)
        self.rightButton = TransparentToolButton(FIF.PAGE_RIGHT, self.imageBar)
        self.switchButton = ToggleButton(self.tr('Switch to Patched Image'),self.imageBar)
        self.showOCRButton = ToggleButton(Icon.TEXT, self.tr('Show OCR Results'),self.imageBar)

        self.listbuttonArea = QFrame(self.indexArea)
        self.listbuttonLayout = QHBoxLayout(self.listbuttonArea) 
        self.listAddButton = PushButton(FIF.ADD,self.tr('Add Image'), self.indexArea)  # 新增按钮
        self.listClearButton = PushButton(Icon.TRUSH,self.tr('Clear'), self.indexArea)  # 清空按钮
        self.deleteCheckedButton = PrimaryPushButton(FIF.DELETE, self.tr('Delete Selected'), self.indexArea)
        

        self.searchBox = SearchBox(self.indexArea)
        self.indexList = ListWidget(self.indexArea)

        # 添加拖放覆盖层
        self.dropCover = InteractiveDropCover(self, base_path=base_path)
        self.dropCover.setGeometry(self.rect())
        self.dropCover.setAcceptDrops(True)
        

        self.progressCover = ProgressCover(self)
        self.progressCover.setGeometry(self.rect())

        self.__initWidget()
    

    def __initWidget(self):
        self.initLayout()

        self.dargButton.installEventFilter(ToolTipFilter(self.dargButton))
        self.zoomInButton.installEventFilter(ToolTipFilter(self.zoomInButton))
        self.zoomOutButton.installEventFilter(ToolTipFilter(self.zoomOutButton))
        self.leftButton.installEventFilter(ToolTipFilter(self.leftButton))
        self.rightButton.installEventFilter(ToolTipFilter(self.rightButton))
        self.switchButton.installEventFilter(ToolTipFilter(self.switchButton))
        self.showOCRButton.installEventFilter(ToolTipFilter(self.showOCRButton))
        
        self.dargButton.setToolTip('Drag Mode')
        self.zoomInButton.setToolTip('Zoom In')
        self.zoomOutButton.setToolTip('Zoom Out')
        self.leftButton.setToolTip('Previous Image')
        self.rightButton.setToolTip('Next Image')
        self.switchButton.setToolTip('Switch to Patched Image')
        self.showOCRButton.setToolTip('Show OCR Results')

        self.switchButton.setEnabled(False)
        self.showOCRButton.setEnabled(False)

        self.searchBox.setClearButtonEnabled(True)
        self.searchBox.setPlaceholderText('Search Image Name')

        self.indexList.setWordWrap(True)
        self.indexList.setIconSize(QSize(64, 64))
        self.indexList.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.indexList.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.deleteCheckedButton.setVisible(False)
        

        self.dropCover.setObjectName('dropCover')
        self.progressCover.setObjectName('progressCover')
        self.picArea.setObjectName('picArea') 
        self.indexArea.setObjectName('indexArea')

        self.connectSignalToSlot()
        
    def connectSignalToSlot(self):

        self.dropCover.dragEnterEvent = self.dragEnterEvent
        self.dropCover.dropEvent = self.dropEvent
        
        self.searchBox.searchSignal.connect(self.search)
        self.searchBox.return_pressed.connect(self.search)
        self.searchBox.clearSignal.connect(self.searchClear)


        self.zoomInButton.clicked.connect(self.viewer.zoom_in)
        self.zoomOutButton.clicked.connect(self.viewer.zoom_out)
        self.dargButton.toggled.connect(self.viewer.set_drag_mode)
        self.leftButton.clicked.connect(self.show_previous_image)
        self.rightButton.clicked.connect(self.show_next_image)
        self.switchButton.toggled.connect(self.switch_image)
        self.showOCRButton.toggled.connect(self.emitOCRResultExpand)

        self.listAddButton.clicked.connect(self.load_file)
        self.listClearButton.clicked.connect(self.clear_images)
        self.indexList.itemChanged.connect(self.update_delete_button_visibility)
        self.deleteCheckedButton.clicked.connect(self.delete_checked_items)

        self.indexList.itemClicked.connect(self.display_selected_image)

        self.patchProgressUpdated.connect(self.progressCover.progressRing.setValue)
        
        
    def initLayout(self):
  
        self.picLayout.addWidget(self.imageBar)

        self.imageBar.addWidget(self.dargButton)
        self.imageBar.addWidget(self.zoomInButton)
        self.imageBar.addWidget(self.zoomOutButton)
        self.imageBar.addWidget(self.leftButton)
        self.imageBar.addWidget(self.rightButton)
        self.imageBar.addWidget(self.switchButton)
        self.imageBar.addWidget(self.showOCRButton)

        self.picLayout.addWidget(self.viewer) 

        
        self.listbuttonLayout.addWidget(self.listAddButton)
        self.listbuttonLayout.addWidget(self.listClearButton)
        
        self.indexLayout.addWidget(self.listbuttonArea,0,Qt.AlignTop)
        self.indexLayout.addWidget(self.searchBox,0,Qt.AlignTop)
        self.indexLayout.addSpacing(10)
        self.indexLayout.addWidget(self.indexList,1,Qt.AlignTop)
        self.indexList.setMaximumHeight(250)
        self.indexLayout.addWidget(self.deleteCheckedButton,0,Qt.AlignBottom)

        self.hBoxLayout.addWidget(self.picArea, 0,)
        self.hBoxLayout.addSpacing(50)
        self.hBoxLayout.addWidget(self.indexArea, 0, Qt.AlignRight)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)

    

    def resizeEvent(self, event):
        self.dropCover.setGeometry(self.rect())
        self.progressCover.setGeometry(self.rect())
        super().resizeEvent(event)

    def set_base_path(self, base_path):
        self.base_path = base_path

    def emitOCRResultExpand(self):
        if self.showOCRButton.isChecked():
            self.ocrResultExpand.emit(True)
            self.show_OCR()
        else:
            self.ocrResultExpand.emit(False)

    def load_file(self):
        if self.indexList.count() > 0 and (self.alreadyPatched or self.evaluatedState):
            InfoBar.error(
                title=self.tr('Error'),
                content=self.tr('Please clear the image list first'),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            return
        file_filter = "Image Files (*.jpg *.jpeg *.png *.webp)"
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", file_filter)
        if file_paths:
            for file_path in file_paths:
                if self.check_new_file(file_path):
                    self.add_to_list(file_path)
            first_item = self.indexList.item(0) if self.indexList.count() > 0 else None
            if first_item:
                self.indexList.setCurrentRow(0)
                self.update_search_completer()
                self.display_selected_image(first_item)
            self.update_list_height()  # 更新高度
            self.dropCover.hide()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            

    def dropEvent(self, event):
        self.dropCover.hide() 
        urls = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if urls:
            uploads_dir = self.uploads_dir
            if os.path.exists(uploads_dir):
                shutil.rmtree(uploads_dir)  # 删除整个目录
            os.makedirs(uploads_dir)
            for file_path in urls:         
                if self.check_new_file(file_path):
                    self.add_to_list(file_path)
            self.indexList.setCurrentRow(0)
            self.update_search_completer()
            self.display_selected_image(self.indexList.item(0))
            self.update_list_height()  # 更新高度




    


    def wheelEvent(self, event):
        if self.indexList.count() == 0:
            event.ignore()  # 忽略当前事件，让它可以传递给父组件
        else:
            super().wheelEvent(event)  # 正常处理滚动事件

    def update_list_height(self):
        item_count = self.indexList.count()
        if item_count > 0:
            total_height = sum([self.indexList.sizeHintForRow(i) for i in range(item_count)])
            spacing = self.indexList.spacing() * (item_count - 1)
            new_height = total_height + spacing
            self.indexList.setFixedHeight(min(new_height, 250))
        else:
            self.indexList.setFixedHeight(0)

    def add_to_list(self, file_path):
        
        new_file_name = os.path.basename(file_path)
        # 文件名不重复，添加到集合和列表中
        self.fileNames.add(new_file_name)

        original_image_path = os.path.join(self.uploads_dir, new_file_name)
        
        # 创建缩略图
        thumbnail_size = QSize(100, 100)  # 设置缩略图的尺寸
        pixmap = QPixmap(original_image_path)
        icon = QIcon(pixmap.scaled(thumbnail_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        item_name = new_file_name
        list_item = QListWidgetItem(icon,item_name)
        list_item.setToolTip(file_path) 
        list_item.setFlags(list_item.flags() | Qt.ItemIsUserCheckable)
        list_item.setCheckState(Qt.Unchecked)
        
        self.indexList.addItem(list_item)
        self.indexList.sortItems(Qt.AscendingOrder)

    def update_delete_button_visibility(self):
        any_checked = any(item.checkState() == Qt.Checked for i in range(self.indexList.count()) for item in [self.indexList.item(i)])
        self.deleteCheckedButton.setVisible(any_checked)
    
    def delete_checked_items(self):

        for i in reversed(range(self.indexList.count())):
            item = self.indexList.item(i)
            if item.checkState() == Qt.Checked:
                file_name = item.text()
                self.fileNames.remove(file_name)
                file_path = os.path.join(self.uploads_dir, file_name)
                os.remove(file_path)
                if self.patchedState:
                    file_path= os.path.join(self.patched_dir, file_name)
                    os.remove(file_path)
                if self.evaluatedState:
                    file_path = os.path.join(self.evaluated_upload_dir, file_name)
                    os.remove(file_path)
                    file_path = os.path.join(self.evaluated_patched_dir, file_name)
                    os.remove(file_path)
                
                self.indexList.takeItem(i)
        self.update_delete_button_visibility()

        if self.indexList.count() == 0:
            self.clear_images()

        else:
            self.indexList.setCurrentRow(0)
            self.display_selected_image(self.indexList.item(0))

    def clear_images(self):
        self.indexList.clear()
        self.fileNames.clear()
        self.dropCover.show()
        self.barchartExpand.emit(False)
        self.patchedState = False
        self.saveornot.emit(False)
        self.switchButton.setChecked(False)
        self.switchButton.setEnabled(False)
        self.evaluatedState = False
        self.alreadyPatched = False

        if self.showOCRButton.isChecked():
            self.showOCRButton.setChecked(False)
            self.ocrResultExpand.emit(False)

        uploads_dir = self.uploads_dir
        if os.path.exists(uploads_dir):
            shutil.rmtree(uploads_dir)  # 删除整个目录
        os.makedirs(uploads_dir)

        patched_dir = self.patched_dir
        if os.path.exists(patched_dir):
            shutil.rmtree(patched_dir)
        os.makedirs(patched_dir)

        evaluated_upload_dir = self.evaluated_upload_dir
        if os.path.exists(evaluated_upload_dir):
            shutil.rmtree(evaluated_upload_dir)
        os.makedirs(evaluated_upload_dir)

        evaluated_patched_dir = self.evaluated_patched_dir
        if os.path.exists(evaluated_patched_dir):
            shutil.rmtree(evaluated_patched_dir)
        os.makedirs(evaluated_patched_dir)

        InfoBar.success(
            title=self.tr('Success'),
            content=self.tr('Image list successfully cleared'),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
    
    def check_new_file(self, file_path):
        new_file_name = os.path.basename(file_path)
        if new_file_name in self.fileNames:
            InfoBar.error(
                title=self.tr('Duplicate Filename'),
                content=new_file_name+"already exists in the list. Please do not add images with duplicate names.",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=5000,
                parent=self
            )
            return False

        # 复制文件到 uploads 文件夹
        self.copy_to_uploads(file_path)

        return True

    def copy_to_uploads(self, original_path):
        uploads_dir = self.uploads_dir
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        new_path = os.path.join(uploads_dir, os.path.basename(original_path))
        shutil.copy(original_path, new_path)
        return new_path
        
    
    def display_selected_image(self, item):
        if item: 
            if self.patchedState:
                if self.evaluatedState:
                    file_path = self.evaluated_patched_dir + '/' + item.text()
                else:
                    file_path = self.patched_dir + '/' + item.text()
            else:
                if self.evaluatedState:
                    file_path = self.evaluated_upload_dir + '/' + item.text()
                else:
                    file_path = self.uploads_dir + '/' + item.text()

            self.viewer.load_image(file_path)
            self.viewer.scale_factor = 1.0
        if self.showOCRButton.isChecked():
            self.show_OCR()

    def update_search_completer(self):
        
        item_texts = [self.indexList.item(i).text() for i in range(self.indexList.count())]
        completer = QCompleter(item_texts, self.searchBox)

        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setMaxVisibleItems(10)
        self.searchBox.setCompleter(completer)
        


    def search(self, searchText):
        self.searchText = searchText
        self.searchResults = self.indexList.findItems(searchText, Qt.MatchFlag.MatchContains)
        if self.searchResults:
            allItems = [self.indexList.item(i) for i in range(self.indexList.count())]
        
            # 隐藏不匹配的项
            for item in allItems:
                item.setHidden(True)  # 先隐藏所有项
            for item in self.searchResults:
                item.setHidden(False)  # 显示匹配的项
  
            self.indexList.setCurrentItem(self.searchResults[0])
            self.display_selected_image(self.searchResults[0])

    def searchClear(self):
        self.searchText = ""
        self.searchResults = []
        self.indexList.setCurrentItem(self.indexList.item(0))
        self.display_selected_image(self.indexList.item(0))
        for i in range(self.indexList.count()):
            self.indexList.item(i).setHidden(False)

    def show_next_image(self):
        current_row = self.indexList.currentRow()
        if current_row < self.indexList.count() - 1:
            next_row = current_row + 1
            self.indexList.setCurrentRow(next_row)
            self.display_selected_image(self.indexList.item(next_row))
    
    def switch_image(self, checked):
        if checked:
            self.switchButton.setChecked(True)
            self.switchButton.setEnabled(True)
            self.switchButton.setText(self.tr('Switch to Original Image'))                                            
            self.patchedState = True
        else:
            self.switchButton.setText(self.tr('Switch to Patched Image'))
            self.patchedState = False

        item = self.indexList.currentItem()
        self.display_selected_image(item)



    def apply_patch(self, strength, style):
        if self.indexList.count() == 0:
            InfoBar.error(
                title=self.tr('Error'),
                content=self.tr('Please add an image first'),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            QTimer.singleShot(500, self.enableButtons.emit)
            return
        
        if self.evaluatedState:
            self.barchartExpand.emit(False)
    
        self.stateTooltip = StateToolTip(
            self.tr('Patching'), self.tr('Please wait'), self.window())
        self.stateTooltip.move(self.stateTooltip.getSuitablePos())
        self.stateTooltip.show()
        self.progressCover.progressRing.setValue(0)
        QTimer.singleShot(400, self.progressCover.show) 
        self.progressCover.raise_()
        uploads_dir = self.uploads_dir
        # 获取uploads目录中的所有文件，确保只选取文件
        upload_files = [os.path.join(uploads_dir, f) for f in os.listdir(uploads_dir) if os.path.isfile(os.path.join(uploads_dir, f))]

        self.thread = PatchThread(upload_files, strength, style, False, base_path=self.base_path)
        self.thread.progressFullUpdated.connect(self.progressCover.progressRing.setValue)  # 连接进度更新信号
        self.thread.patchFullCompleted.connect(self.add_patched_images_to_list)  # 连接补丁完成信号
        self.thread.start()
        

    def add_patched_images_to_list(self, patched_img_paths):

        self.indexList.clear()
        self.fileNames.clear()
        for img_path in patched_img_paths:
            self.add_to_list(img_path)
        self.indexList.setCurrentRow(0)
        self.update_search_completer()
        self.alreadyPatched = True
        self.evaluatedState = False
        self.saveornot.emit(True)
        self.switch_image(True)
        
        self.update_list_height()  # 更新高度
        QTimer.singleShot(1000, self.progressCover.hide)
        self.stateTooltip.setContent(
            self.tr('Patch application completed!') + ' 😆')
        self.stateTooltip.setState(True)

        if self.showOCRButton.isChecked():
            self.showOCRButton.setChecked(False)
            self.ocrResultExpand.emit(False)
        self.showOCRButton.setEnabled(False)

        QTimer.singleShot(1000, self.enableButtons.emit)
    
    def evaluate(self, model):
        if self.indexList.count() == 0:
            InfoBar.error(
                title=self.tr('Error'),
                content=self.tr('Please add an image first'),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            QTimer.singleShot(500, self.enableButtons.emit)
            return
        if not self.alreadyPatched:
            InfoBar.error(
                title=self.tr('Error'),
                content=self.tr('Please apply a patch before evaluation'),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
            QTimer.singleShot(500, self.enableButtons.emit)
            return
        self.stateTooltip = StateToolTip(
            self.tr('Evaluating'), self.tr('Please wait'), self.window())
        self.stateTooltip.move(self.stateTooltip.getSuitablePos())
        self.stateTooltip.show()
        self.progressCover.progressRing.setValue(0)
        QTimer.singleShot(400, self.progressCover.show) 
        self.progressCover.raise_()
        uploads_dir = self.uploads_dir
        upload_files = [os.path.join(uploads_dir, f) for f in os.listdir(uploads_dir) if os.path.isfile(os.path.join(uploads_dir, f))]

        patched_dir = os.path.join(self.base_path, 'results/patched_images')
        patched_files = [os.path.join(patched_dir, f) for f in os.listdir(patched_dir) if os.path.isfile(os.path.join(patched_dir, f))]
        
        self.thread = EvaluateThread(upload_files, patched_files, model, True, base_path=self.base_path)
        self.thread.progressFullUpdated.connect(self.progressCover.progressRing.setValue)
        self.thread.evaluateFullCompleted.connect(self.add_evaluated_images_to_list)  # 连接补丁完成信号
        self.thread.start()
        
    def add_evaluated_images_to_list(self, evaluate_results):

        averages = self.calculate_averages(evaluate_results)
        categories = self.counter(evaluate_results)
        data = (averages, categories)
        self.updateChart.emit(data)

        self.evaluatedState = True
        self.evaluate_results = evaluate_results
        self.indexList.clear()
        self.fileNames.clear()

        for i in range(len(evaluate_results)):
            result = evaluate_results[i]
            img_name = result["image_name"]
            patched_image_path = self.evaluated_patched_dir + '/' + img_name
            self.add_to_list(patched_image_path)

        self.update_search_completer()
        self.indexList.setCurrentRow(0)
        self.switch_image(True)
        self.update_list_height()  # 更新高度
        QTimer.singleShot(1000, self.progressCover.hide)
        self.stateTooltip.setContent(
            self.tr('Evaluation completed!') + ' 😆')
        self.stateTooltip.setState(True) 
        QTimer.singleShot(1000, lambda:self.barchartExpand.emit(True))  
        self.showOCRButton.setEnabled(True)
        QTimer.singleShot(1000, self.enableButtons.emit)

    def handle_inital_image(self, file_paths):
        for file_path in file_paths:
            if self.check_new_file(file_path):
                self.add_to_list(file_path)
        self.indexList.setCurrentRow(0)
        self.update_search_completer()
        self.display_selected_image(self.indexList.item(0))
        self.update_list_height()
        self.dropCover.hide()

        

        
        
    def calculate_averages(self, results):
        total = len(results)

        # 保留两位小数
        avg_metrics = {
            "P": round(Decimal(sum(item["P"] for item in results) / total), 4)*100,
            "R": round(Decimal(sum(item["R"] for item in results) / total), 4)*100,
            "F": round(Decimal(sum(item["F"] for item in results) / total), 4)*100,
            "recognized_character_rate": round(Decimal(sum(item["recognized_character_rate"] for item in results) / total), 2),
            "attack_success_rate": round(Decimal(sum(item["attack_success_rate"] for item in results) / total), 2),
            "average_edit_distance": round(Decimal(sum(item["average_edit_distance"] for item in results) / total), 2),
        }
        return avg_metrics

    
    def counter(self, results):
        categories = {self.tr('Excellent'): 0, self.tr('Good'): 0, self.tr('Fair'): 0}
        for result in results:
            # 计算综合评分，这里假设越低越好
            combined_score = 1 - (0.4 * result['P'] + 0.4 * result['R'] + 0.2 * result['F'])
            # 分类
            if combined_score > 0.8:
                categories[self.tr('Excellent')] += 1
            elif combined_score > 0.5:
                categories[self.tr('Good')] += 1
            else:
                categories[self.tr('Fair')] += 1
        return categories



    def show_previous_image(self):
        current_row = self.indexList.currentRow()
        if current_row > 0:
            previous_row = current_row - 1
            self.indexList.setCurrentRow(previous_row)
            self.display_selected_image(self.indexList.item(previous_row))


    def show_OCR(self):
        # 展示当前图像Patch前后OCR识别结果的变化
        img_name = self.indexList.currentItem().text()
        # 从评估结果中找到对应的结果
        original_text = ''
        patched_text = ''
        for result in self.evaluate_results:
            if result["image_name"] == img_name:
                original_ocr_result = result["ocr_result_clean"]["texts"]
                patched_ocr_result = result["ocr_result_full"]["texts"]

        original_text = " ".join(original_ocr_result)
        patched_text = " ".join(patched_ocr_result)
        
        matcher = SequenceMatcher(None, original_text, patched_text)
        patched_marked = []

        # 标记差异
        for op, o_start, o_end, p_start, p_end in matcher.get_opcodes():
            if op == 'replace':
                # 仅在底纹图结果中标记差异
                patched_marked.append(f"<span style='color: red;'>{patched_text[p_start:p_end]}</span>")
            elif op == 'delete':
                patched_marked.append(f"<span style='color: red;'>{original_text[o_start:o_end]}</span>")

            elif op == 'equal':
                patched_marked.append(patched_text[p_start:p_end])

        # 组合标记后的结果
        patched_marked = ''.join(patched_marked)

        self.ocrResult.emit([original_text, patched_marked, patched_text])


class ProtectArea(QWidget):
    applyPatch = Signal(int, str)
    evaluate = Signal(str)
    disableButtons = Signal()
    
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent=parent)
        self.setObjectName('protectArea')
        self.base_path = base_path
        self.patch_info_path = os.path.join(self.base_path, 'patches', 'patch.json')

        self.modelInfoActivated = False

        self.hBoxLayout = QHBoxLayout(self)
        self.patchArea = QFrame(self)
        self.evaluateArea = QFrame(self)


        self.patchLayout = QHBoxLayout(self.patchArea)
        self.evaluateLayout = QVBoxLayout(self.evaluateArea)
        self.modelsettingArea = QFrame(self.evaluateArea)
        self.modelsettingLayout = QHBoxLayout(self.modelsettingArea)

        self.settingArea = QFrame(self)
        self.settingLayout = QVBoxLayout(self.settingArea)

        self.strengthArea = QFrame(self.settingArea)
        self.strengthLayout = QHBoxLayout(self.strengthArea)

        self.strenthLabel = QLabel(self.tr('Select Patch Strength'), self)
        self.strenthButton = ComboBox(self)

        self.styleArea = QFrame(self.settingArea)
        self.styleLayout = QHBoxLayout(self.styleArea)

        self.styleLabel = QLabel(self.tr('Select Patch Style'), self)
        self.styleButton = ComboBox(self)

        self.previewArea = QFrame(self)
        self.previewLayout = QVBoxLayout(self.previewArea)
        
        self.previewLabel = QLabel(self.tr('Patch Preview'),self)

        self.previewPatchArea = QFrame(self)
        self.previewPatchLayout = QVBoxLayout(self.previewPatchArea)
        self.previewPatch = ImageLabel(self)

        self.savePatchButton = PrimaryPushButton(self.tr('Export Image'), self)

        self.patchConfirmButton = PrimaryPushButton( self.tr('Add Patch'), self)

        self.modelLabel = QLabel(self.tr('Select Model'), self)
        self.modelButton = ComboBox(self)

        self.evaluateConfirmButton = PrimaryPushButton(self.tr('Evaluate'), self)

        self.modelInfoArea = QFrame(self)
        self.modelInfoLayout = QHBoxLayout(self.modelInfoArea)

        self.__initWidget()

    def __initWidget(self):
        self.initLayout()

        self.updateStyleList()

        self.strenthButton.addItems([
            '25%',
            '50%',
            '75%',
            '100%'
        ])

        self.previewPatchArea.setStyleSheet("""
            QFrame {
                border: 2px dashed #0078D7; /* 设置虚线边框 */
                border-radius: 5px; /* 边框圆角 */
            }
        """)

        self.strenthButton.setFixedWidth(80)
        self.savePatchButton.setDisabled(True)
        self.previewLabel.setAlignment(Qt.AlignCenter)
        self.previewLabel.setFixedWidth(100)
        font = QFont()
        font.setPointSize(12)
        self.previewLabel.setFont(font)

        self.previewPatchArea.setFixedSize(100, 100)
        self.previewPatch.setFixedSize(90, 90)
        self.previewPatch.setAlignment(Qt.AlignCenter)

        self.previewPatch.setScaledContents(False)
        self.updatePreview()

        self.modelLabel.setFixedWidth(60)
        self.modelButton.addItems([
            'EasyOCR',
            'PaddleOCR'
        ])
        self.modelButton.setFixedWidth(150)

        self.evaluateConfirmButton.setFixedWidth(100)

        self.modelButton.setCurrentIndex(0)
        self.patchArea.setFixedWidth(400)
        self.evaluateArea.setFixedWidth(400)

        self.updateModelInfo()

        self.connectSignalToSlot()
        
    def connectSignalToSlot(self):

        self.strenthButton.currentIndexChanged.connect(self.updatePreview)
        self.styleButton.currentIndexChanged.connect(self.updatePreview)
        self.patchConfirmButton.clicked.connect(self.emitApplyPatchSignal)
        self.modelButton.currentIndexChanged.connect(self.updateModelInfo)
        self.evaluateConfirmButton.clicked.connect(self.emitEvaluateSignal)

        self.disableButtons.connect(self.disableUI)
        self.savePatchButton.clicked.connect(self.savePatchedImage)
        
        
        
    def initLayout(self):


        self.hBoxLayout.addWidget(self.patchArea,1)
        self.hBoxLayout.addWidget(self.evaluateArea,1)

        self.patchLayout.addWidget(self.settingArea)
        self.patchLayout.addWidget(self.previewArea)

        self.settingLayout.addWidget(self.strengthArea,1,Qt.AlignTop)
        self.settingLayout.addWidget(self.styleArea,1,Qt.AlignTop)
        self.settingLayout.addWidget(self.patchConfirmButton,1,Qt.AlignTop)
        self.settingLayout.addWidget(self.savePatchButton,1,Qt.AlignTop)

        self.strengthLayout.addWidget(self.strenthLabel)
        self.strengthLayout.addWidget(self.strenthButton)

        self.styleLayout.addWidget(self.styleLabel)
        self.styleLayout.addWidget(self.styleButton)
        
        self.previewLayout.addWidget(self.previewLabel,1,Qt.AlignCenter)
        self.previewLayout.addWidget(self.previewPatchArea,1,Qt.AlignCenter)

        self.previewPatchLayout.addWidget(self.previewPatch)

        

        self.modelsettingLayout.addWidget(self.modelLabel)
        self.modelsettingLayout.addWidget(self.modelButton)
        self.modelsettingLayout.addWidget(self.evaluateConfirmButton)

        self.evaluateLayout.addWidget(self.modelsettingArea,0)
        self.evaluateLayout.addWidget(self.modelInfoArea,0)
    
    def updateStyleList(self):
        self.patch_infos = load_patch_info(self.patch_info_path)["patches"]

        for patch_info in self.patch_infos:
            patch_name = patch_info["patch_name"]
            self.styleButton.addItem(patch_name)

    def updatePreview(self):

        patch_name = self.styleButton.currentText()

        for patch_info in self.patch_infos:
            if patch_info["patch_name"] == patch_name:
                priview_path= patch_info["patch_preview"]
                break

        pixmap = QPixmap(priview_path)
        self.previewPatch.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio))
    
    def emitApplyPatchSignal(self):
        # 触发 applyPatch 信号的逻辑
        self.disableButtons.emit()
        patch_strength = int(self.strenthButton.currentText().replace('%', ''))
        patch_style = self.styleButton.currentText()
        self.applyPatch.emit(patch_strength, patch_style)

    def savePatchedImage(self):
        w = CustomMessageBox(self.window(), self.base_path)
        w.exec()

    
    def updateModelInfo(self):

        if not self.modelInfoActivated:
            self.modelInfo = InfoBar.info(
                title=self.tr('Model info'),
                content=self.tr('Model info'),
                orient=Qt.Vertical,
                isClosable=False,
                position=InfoBarPosition.NONE,
                duration=-1,
                parent=self
            )
            self.evaluateLayout.addWidget(self.modelInfo)
            self.modelInfoActivated = True

        model_index = self.modelButton.currentIndex()   
        if model_index == 0:  # EasyOCR
            content = self.tr('The model architectures of services like EasyOCR, KerasOCR, etc.')
            self.serviceIcon1 = IconWidget(QIcon(':/gallery/images/icons/EasyOCR.svg'), self.modelInfo)
            self.serviceIcon2 = IconWidget(QIcon(':/gallery/images/icons/Keras.svg'), self.modelInfo)
        elif model_index == 1:  # PaddleOCR
            content = self.tr('The model architectures of services such as WeChat OCR, PaddleOCR, etc.')
            self.serviceIcon1 = IconWidget(QIcon(':/gallery/images/icons/Wechat.svg'), self.modelInfo)
            self.serviceIcon2 = IconWidget(QIcon(':/gallery/images/icons/PaddlePaddle.svg'), self.modelInfo)
        self.modelInfo.close()

        self.modelInfo = InfoBar.info(
                title=self.tr('Model info'),
                content=content,
                orient=Qt.Vertical,
                isClosable=False,
                position=InfoBarPosition.NONE,
                duration=-1,
                parent=self
            )
        self.modelInfo.setFixedWidth(300)
        
        self.serviceIcon1.setFixedSize(40, 40)
        self.serviceIcon2.setFixedSize(40, 40)
        self.serviceIconArea = QWidget(self.modelInfo)
        self.serviceIconLayout = QHBoxLayout(self.serviceIconArea)
        self.serviceIconLayout.addWidget(self.serviceIcon1)
        self.serviceIconLayout.addSpacing(20)  
        self.serviceIconLayout.addWidget(self.serviceIcon2)


        self.modelInfo.addWidget(self.serviceIconArea)
        
        self.modelInfoLayout.addWidget(self.modelInfo,1)

    def emitEvaluateSignal(self):
        
        self.disableButtons.emit()
        model_index = self.modelButton.currentIndex()
        if model_index == 0:
            self.evaluate.emit('easyocr')
        elif model_index == 1:
            self.evaluate.emit('paddleocr')

    def disableUI(self):
        # 禁用按钮以防止多次点击
        self.patchConfirmButton.setEnabled(False)
        self.evaluateConfirmButton.setEnabled(False)

    def enableUI(self):
        # 操作后重新启用按钮
        self.patchConfirmButton.setEnabled(True)
        self.evaluateConfirmButton.setEnabled(True)

class OCRResultsArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('ocrResultsArea')

        self.hBoxLayout = QHBoxLayout(self)
        self.ocrArea1 = QFrame(self)
        self.ocrLayout1 = QVBoxLayout(self.ocrArea1)

        self.ocrLabel1 = QLabel(self.tr('OCR Results for Original Image'), self)
        self.ocrText1 = TextEdit(self)
        self.exportButton1 = PushButton(self.tr('Export Results'), self)

        self.arrowIcon = IconWidget(FIF.RIGHT_ARROW, self)

        self.ocrArea2 = QFrame(self)
        self.ocrLayout2 = QVBoxLayout(self.ocrArea2)

        self.ocrLabel2 = QLabel(self.tr('OCR Results for Patched Image'), self)
        self.ocrText2 = TextEdit(self)
        self.exportButton2 = PushButton(self.tr('Export Results'), self)

        self.rawText1 = ''
        self.rawText2 = ''

        self.__initWidget()

    def __initWidget(self):
        self.initLayout()
        self.arrowIcon.setFixedSize(40, 40)
        self.ocrLabel1.setFont(QFont('Arial', 12))
        self.ocrLabel2.setFont(QFont('Arial', 12))

        self.connectSignalToSlot()

    def connectSignalToSlot(self):

        self.exportButton1.clicked.connect(lambda: self.export_result(self.rawText1, 'original'))
        self.exportButton2.clicked.connect(lambda: self.export_result(self.rawText2, 'patched'))


    def initLayout(self):
        self.ocrLayout1.addWidget(self.ocrLabel1)
        self.ocrLayout1.addWidget(self.ocrText1)
        self.ocrLayout1.addWidget(self.exportButton1)
        self.hBoxLayout.addWidget(self.ocrArea1)

        self.hBoxLayout.addWidget(self.arrowIcon)

        self.ocrLayout2.addWidget(self.ocrLabel2)
        self.ocrLayout2.addWidget(self.ocrText2)
        self.ocrLayout2.addWidget(self.exportButton2)
        self.hBoxLayout.addWidget(self.ocrArea2)

        self.setMaximumHeight(0)

    def show_result(self, ocr_result):

        self.rawText1 = ocr_result[0]
        self.rawText2 = ocr_result[2]

        self.ocrText1.setMarkdown(ocr_result[0])
        self.ocrText2.setMarkdown(ocr_result[1])

    def export_result(self, text, type):
        # Function to save the text to a file
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, f"Save OCR Results - {type}", "", "Text Files (*.txt);;All Files (*)", options=options)
        if fileName:
            with open(fileName, 'w', encoding='utf-8') as file:
                file.write(text)

class ChartArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
        self.hBoxLayout = QHBoxLayout(self)
        self.chart1 = QWebEngineView(self)
        self.chart2 = QWebEngineView(self)
        
        self.__initWidget()
    
    def __initWidget(self):
        self.initLayout()

        self.chart1.setFixedWidth(440)
        self.chart2.setFixedWidth(340)

        self.chart1.setContextMenuPolicy(Qt.NoContextMenu)
        self.chart2.setContextMenuPolicy(Qt.NoContextMenu)

        self.connectSignalToSlot()

    def connectSignalToSlot(self):

        pass

    def initLayout(self):
        
        self.hBoxLayout.addWidget(self.chart1)
        self.hBoxLayout.addWidget(self.chart2)
        
        
    def update_chart(self, data):

        averages, categories = data
        
        self.create_radar(averages)
        self.create_pie(categories)

    def create_radar(self, data):
        
        radar = Radar(init_opts=opts.InitOpts(width="420px", height="300px"))
        radar.add_schema(
            schema=[
                opts.RadarIndicatorItem(name=self.tr("Precision")+"(%)", max_=100),
                opts.RadarIndicatorItem(name=self.tr("Recall")+"(%)", max_=100),
                opts.RadarIndicatorItem(name=self.tr("Hmean")+"(%)", max_=100),
                opts.RadarIndicatorItem(name=self.tr("Recognized Rate")+"(%)", max_=100),
                opts.RadarIndicatorItem(name=self.tr("Protect Success Rate")+"(%)", max_=100),
                opts.RadarIndicatorItem(name=self.tr("Edit Distance"), max_=50)
            ],
            shape="circle",
            radius="100px",
            center=["50%", "55%"],
            start_angle=90,
            
            axisline_opt=opts.AxisLineOpts(
                linestyle_opts=opts.LineStyleOpts(
                    color ='rgba(211, 253, 250, 0.8)'
                )
            ),
            splitline_opt=opts.SplitLineOpts(
                is_show=True,
                linestyle_opts=opts.LineStyleOpts(
                    color ='rgba(211, 253, 250, 0.8)'
                )
            ),
            splitarea_opt=opts.SplitAreaOpts(
                is_show=True,
                areastyle_opts=opts.AreaStyleOpts(
                    opacity=0.9,
                    color=['#77EADF', '#26C3BE', '#64AFE9', '#428BD4', '#3D76B6'],
                )
            ),
            textstyle_opts=opts.TextStyleOpts(
                color="#428BD4",
                font_size=12,
            ),

        )

        radar.add("评估参数", [list(data.values())],linestyle_opts=opts.LineStyleOpts(width=1.5), areastyle_opts=opts.AreaStyleOpts(opacity=0.4), color='rgb(255, 228, 52)',tooltip_opts=opts.TooltipOpts(is_show=True, trigger="item", trigger_on="mousemove|click", axis_pointer_type="line",textstyle_opts=opts.TextStyleOpts(font_size=10)))
        
        self.chart1.setHtml(radar.render_embed())

    def create_pie(self, count):

        pie = Pie(init_opts=opts.InitOpts(width="320px", height="300px"))
        pie_data = [(name, value) for name, value in count.items()]
        pie.add("", pie_data, radius=["30%", "75%"], center=["50%", "55%"],label_opts=opts.LabelOpts(is_show=False))
        pie.set_colors(["#008000", "#90EE90", "#FFFF99"])
        self.chart2.setHtml(pie.render_embed())

class CustomMessageBox(MessageBoxBase):
    """ Custom message box """

    def __init__(self, parent=None,base_path=None):
        super().__init__(parent)
        self.patched_dir = os.path.join(base_path, 'results/patched_images')
        self.folder = None
        self.settingArea = QFrame(self)
        self.confirmArea = QFrame(self)

        self.settingLayout = QVBoxLayout(self.settingArea)
        self.confirmLayout = QHBoxLayout(self.confirmArea)

        self.formatArea = QFrame(self.settingArea)
        self.formatLayout = QHBoxLayout(self.formatArea)

        self.formatLabel = QLabel(self.tr('Select Save Format'), self)
        self.formatButton = ComboBox(self.settingArea)

        self.pathArea = QFrame(self.settingArea)
        self.pathLayout = QHBoxLayout(self.pathArea)

        self.pathLabel = QLabel(self.tr('Select Save Directory'), self)
        self.pathedit = LineEdit(self.pathArea)
        self.pathButton = PrimaryToolButton(FIF.FOLDER, self.pathArea)
        self.saveProgress = ProgressRing(self.confirmArea)


        self.widget.setMinimumWidth(360)
        # self.yesButton.setDisabled(True)
        self.__initWidget()

    def __initWidget(self):
        self.initLayout()
        
        self.yesButton.setText(self.tr('Save'))
        self.yesButton.setIcon(FIF.SAVE)
        self.cancelButton.setText(self.tr('Cancel'))

        self.formatButton.addItems([
            '使用原图格式',
            'jpg',
            'png',
            'webp'
        ])

        self.saveProgress.setTextVisible(True)

        self.connectSignalToSlot()

    def connectSignalToSlot(self):

        self.yesButton.clicked.connect(self.save_file)
        self.pathButton.clicked.connect(self.select_dir)

    def initLayout(self):
        
        self.formatLayout.addWidget(self.formatLabel)
        self.formatLayout.addWidget(self.formatButton)
        self.formatArea.setFixedWidth(300)

        self.pathLayout.addWidget(self.pathLabel)
        self.pathLayout.addWidget(self.pathedit)
        self.pathLayout.addWidget(self.pathButton)
        self.pathArea.setFixedWidth(300)

        self.settingLayout.addWidget(self.formatArea)
        self.settingLayout.addWidget(self.pathArea)
        self.settingLayout.setContentsMargins(0, 0, 0, 0)

        self.confirmLayout.addWidget(self.saveProgress)

        self.viewLayout.addWidget(self.settingArea)
        self.viewLayout.addWidget(self.confirmArea)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)

    def select_dir(self):

        self.folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        
        if self.folder:
            
            self.pathedit.setText(self.folder)

    def save_file(self):

        if not self.folder:
            w = MessageBox('Error', '请选择保存目录', self.window())
            w.exec()

        else:
            # 保存patched_dir中的所有图像到指定目录，以指定的格式
            file_format = self.formatButton.currentText()
            for file_name in os.listdir(self.patched_dir):
                file_path = os.path.join(self.patched_dir, file_name)
                if file_format == '使用原图格式':
                    shutil.copy(file_path, self.folder)
                else:
                    new_file_name = file_name.split('.')[0] + '.' + file_format
                    new_file_path = os.path.join(self.folder, new_file_name)
                    shutil.copy(file_path, new_file_path)


class PatchAllPage(ScrollArea):

    def __init__(self,parent=None, base_path = None):
        super().__init__(parent=parent)

        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        self.visualizationArea = VisualizationArea(self, base_path=base_path)
        self.ocrResultsArea = OCRResultsArea(self)
        self.chartArea = ChartArea(self)
        self.protectionArea = ProtectArea(self, base_path=base_path)   

        self.__initWidget()
    
    def __initWidget(self):
        self.initLayout()
        self.view.setObjectName('view')
        self.setObjectName('patchAllPage')
        StyleSheet.PATCH_ALL_PAGE.apply(self)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)


        self.connectSignalToSlot()

    def connectSignalToSlot(self):

        self.protectionArea.applyPatch.connect(self.visualizationArea.apply_patch)
        self.protectionArea.evaluate.connect(self.visualizationArea.evaluate)
        self.visualizationArea.barchartExpand.connect(self.barchart_show)
        self.visualizationArea.updateChart.connect(self.chartArea.update_chart)
        self.visualizationArea.enableButtons.connect(self.protectionArea.enableUI)
        self.visualizationArea.saveornot.connect(self.protectionArea.savePatchButton.setEnabled)
        self.visualizationArea.ocrResultExpand.connect(self.ocrresults_show)
        self.visualizationArea.ocrResult.connect(self.ocrResultsArea.show_result)

        signalBus.initialImageSignal_full.connect(self.visualizationArea.handle_inital_image)

    def initLayout(self):
        
        self.vBoxLayout.addSpacing(10)
        self.visualizationArea.setFixedHeight(425)
        self.visualizationArea.dropCover.setStyleSheet(f'''
            padding: {self.visualizationArea.height()//4}px;
        ''')
        self.vBoxLayout.addWidget(self.visualizationArea, 1, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.ocrResultsArea, 0, Qt.AlignTop)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.chartArea, 1, Qt.AlignTop)
        self.vBoxLayout.addSpacing(5)
        self.vBoxLayout.addWidget(self.protectionArea, 0, Qt.AlignTop)


        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.vBoxLayout.setContentsMargins(36, 0, 36, 0)

    
    def ocrresults_show(self, show):
        if show:
            self.animation1 = QPropertyAnimation(self.ocrResultsArea, b"minimumHeight")
            self.animation1.setDuration(500)
            self.animation1.setStartValue(0) 
            self.animation1.setEndValue(300)  
            self.animation1.setEasingCurve(QEasingCurve.InOutQuart)  
            self.animation1.start()
        else:
            height = self.ocrResultsArea.height()
            self.animation1 = QPropertyAnimation(self.ocrResultsArea, b"minimumHeight")
            self.animation1.setDuration(1000)  
            self.animation1.setStartValue(height)  
            self.animation1.setEndValue(0) 
            self.animation1.setEasingCurve(QEasingCurve.InOutQuart)
            self.animation1.start()
            

    def barchart_show(self, show):
        height = self.chartArea.height()
        if show:
            self.animation2 = QPropertyAnimation(self.chartArea, b"minimumHeight")
            self.animation2.setDuration(1000) 
            self.animation2.setStartValue(height) 
            self.animation2.setEndValue(340) 
            self.animation2.setEasingCurve(QEasingCurve.InOutQuart)  
            self.animation2.start()
        else:

            self.animation2 = QPropertyAnimation(self.chartArea, b"minimumHeight")
            self.animation2.setDuration(1000)  
            self.animation2.setStartValue(height) 
            self.animation2.setEndValue(0)  
            self.animation2.setEasingCurve(QEasingCurve.InOutQuart) 
            self.animation2.start()




    