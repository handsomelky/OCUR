from PySide6.QtCore import QModelIndex, Qt, QObject, QEvent, Signal, QTimer, QSize, QPropertyAnimation, QEasingCurve, QUrl
from PySide6.QtGui import QPainter, QColor, QPixmap, QPen, QIcon, QFont
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFileDialog, QFrame, QGraphicsView, QListWidgetItem, QLabel, QGraphicsPixmapItem, QGraphicsScene, QScrollArea, QCompleter
from PySide6.QtWebEngineWidgets import QWebEngineView

from pyecharts.charts import Radar, Pie
from pyecharts import options as opts

import os
import shutil
import sys
from difflib import SequenceMatcher

from qfluentwidgets import ScrollArea,  TransparentToolButton, TransparentToggleToolButton, ListWidget, PushButton, SearchLineEdit, ComboBox, PrimaryPushButton, ProgressRing, LineEdit, ToggleButton, PrimaryToolButton, ScrollArea, CommandBar, ToolTipFilter, IconWidget, InfoBar, InfoBarPosition, ImageLabel, StateToolTip, MessageBoxBase, MessageBox, TextEdit
from qfluentwidgets import FluentIcon as FIF
from ..common.config import cfg, HELP_URL, REPO_URL, EXAMPLE_URL, FEEDBACK_URL
from ..common.icon import Icon
from ..components.link_card import LinkCardView
from ..components.sample_card import SampleCardView
from ..common.style_sheet import StyleSheet
from ..common.signal_bus import signalBus

from ..components.graph_scene import GraphScene,GraphicsImageItem, GraphicsPolygonItem

from ..api.patch import PatchThread
from ..api.evaluate import EvaluateThread




class ImageViewer(QWidget):
    
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.picScene = GraphScene()
        self.view = QGraphicsView(self.picScene, self)

        self.view.setScene(self.picScene)

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


class InteractiveDropCover(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
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
    applyPatch = Signal()
    patchProgressUpdated = Signal(int)
    barchartExpand = Signal(bool)
    updateChart = Signal(dict)
    enableButtons = Signal()
    saveornot = Signal(bool)
    ocrResult = Signal(list)
    ocrResultExpand = Signal(bool)

    def __init__(self, parent=None, base_path=None):
        super().__init__(parent=parent)

        self.base_path = base_path
        self.upload_file = None

        self.originalParent = None
        self.originalLayoutIndex = None
        self.patchedState = False
        self.alreadyPatched = False
        self.evaluatedState = False
        self.selectRects = []

        self.patched_dir = os.path.join(base_path, 'results/patched_image_part')
        self.evaluated_upload_dir = os.path.join(base_path, 'results/evaluated_upload_image_part')
        self.evaluated_patched_dir = os.path.join(base_path, 'results/evaluated_patched_image_part')

        self.hBoxLayout = QHBoxLayout(self)
        self.picArea = QFrame(self)
        self.textArea = QFrame(self)

        self.picLayout = QVBoxLayout(self.picArea)
        self.textLayout = QVBoxLayout(self.textArea)

        self.imageBar = CommandBar(self)
        

        self.viewer = ImageViewer(self.picArea)  # 使用自定义的图像查看器

        self.dargButton = TransparentToggleToolButton(FIF.MOVE, self.imageBar)
        self.zoomInButton = TransparentToolButton(FIF.ZOOM_IN, self.imageBar)
        self.zoomOutButton = TransparentToolButton(FIF.ZOOM_OUT, self.imageBar)
        self.switchButton = ToggleButton(self.tr('Switch to Patched Image'),self.imageBar)
        self.restoreButton = PrimaryPushButton(FIF.HISTORY,self.tr('Restore to Original Image'), self.imageBar)
        
        self.listClearButton = PushButton(Icon.TRUSH,self.tr('Clear'), self.textArea)
        self.textList = ListWidget(self.textArea)
        self.patchCheckedButton = PrimaryPushButton (self.tr('Add Patch to Selected Area'), self.textArea)

        # 添加拖放覆盖层
        self.dropCover = InteractiveDropCover(self)
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
        self.switchButton.installEventFilter(ToolTipFilter(self.switchButton))
        self.restoreButton.installEventFilter(ToolTipFilter(self.restoreButton))
        
        
        
        self.dargButton.setToolTip('Drag Mode')
        self.zoomInButton.setToolTip('Zoom In')
        self.zoomOutButton.setToolTip('Zoom Out')
        self.switchButton.setToolTip('Switch to Patched Image')
        self.restoreButton.setToolTip('Restore to Original Image')
        

        self.switchButton.setEnabled(False)

        self.textList.setWordWrap(True)
        self.textList.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.textList.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.patchCheckedButton.setVisible(False)
        

        self.dropCover.setObjectName('dropCover')
        self.progressCover.setObjectName('progressCover')
        self.picArea.setObjectName('picArea') 
        self.textArea.setObjectName('textArea')

        self.connectSignalToSlot()
        
    def connectSignalToSlot(self):

        self.dropCover.dragEnterEvent = self.dragEnterEvent
        self.dropCover.dropEvent = self.dropEvent


        self.zoomInButton.clicked.connect(self.viewer.zoom_in)
        self.zoomOutButton.clicked.connect(self.viewer.zoom_out)
        self.dargButton.toggled.connect(self.viewer.set_drag_mode)

        self.switchButton.toggled.connect(self.switch_image)
        
        self.listClearButton.clicked.connect(self.clear_images)
        self.textList.itemChanged.connect(self.handleItemChanged)
        self.patchCheckedButton.clicked.connect(self.emitApplyPatchSignal)

        self.patchProgressUpdated.connect(self.progressCover.progressRing.setValue)

        self.restoreButton.clicked.connect(self.restore_image)
        
        
    def initLayout(self):
  
        self.picLayout.addWidget(self.imageBar)

        self.imageBar.addWidget(self.dargButton)
        self.imageBar.addWidget(self.zoomInButton)
        self.imageBar.addWidget(self.zoomOutButton)
        self.imageBar.addWidget(self.switchButton)
        self.imageBar.addWidget(self.restoreButton)
        

        self.picLayout.addWidget(self.viewer) 
        
        self.textLayout.addWidget(self.listClearButton,0,Qt.AlignTop)
        self.textLayout.addWidget(self.textList,1,Qt.AlignTop)
        
        self.textList.setMaximumHeight(350)
        self.textLayout.addWidget(self.patchCheckedButton,0,Qt.AlignBottom)

        self.hBoxLayout.addWidget(self.picArea, 0,)
        self.hBoxLayout.addSpacing(50)
        self.hBoxLayout.addWidget(self.textArea, 0, Qt.AlignRight)
        self.hBoxLayout.setContentsMargins(0, 0, 0, 0)

    

    def resizeEvent(self, event):
        self.dropCover.setGeometry(self.rect())
        self.progressCover.setGeometry(self.rect())
        super().resizeEvent(event)
    
    def restore_image(self):
        self.alreadyPatched = False
        self.display_image('paddleocr')

    def emitApplyPatchSignal(self):

        self.applyPatch.emit()


    def load_file(self):
        if self.upload_file is not None:
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
        file_filter = "Image File (*.jpg *.jpeg *.png)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", file_filter)
        if file_path:
            self.upload_file = file_path
            
            self.display_image('paddleocr')

            QTimer.singleShot(500, lambda:self.dropCover.hide())

            

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            

    def dropEvent(self, event):
        urls = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if len(urls)==1:
            self.upload_file = urls[0]
            self.display_image('paddleocr')
            QTimer.singleShot(500, lambda:self.dropCover.hide())

        elif len(urls)>1:
            InfoBar.error(
                title=self.tr('Error'),
                content=self.tr('Only one image can be uploaded'),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )


    def wheelEvent(self, event):
        if self.textList.count() == 0:
            event.ignore()  # 忽略当前事件，让它可以传递给父组件
        else:
            super().wheelEvent(event)  # 正常处理滚动事件

    def update_list_height(self):
        item_count = self.textList.count()
        if item_count > 0:
            total_height = sum([self.textList.sizeHintForRow(i) for i in range(item_count)])
            spacing = self.textList.spacing() * (item_count - 1)
            new_height = total_height + spacing
            self.textList.setFixedHeight(min(new_height, 300))
        else:
            self.textList.setFixedHeight(0)

    def updateView(self, recognitions, image_file):
        """
        更新图片和识别信息
        """

        # 清空当前所有图元
        self.viewer.picScene.clear()
        if not self.alreadyPatched:
            self.currentRecognitions = recognitions
        # 添加图片
        self.imageItem = GraphicsImageItem(image_file, self.viewer.picScene)
        # 添加框
        for index, item in enumerate(recognitions):
            GraphicsPolygonItem(item, index, self.viewer.picScene, self.textList)

        self.viewer.view.setSceneRect(self.imageItem.boundingRect())  # 确保场景大小匹配图像大小
        self.viewer.view.fitInView(self.imageItem, Qt.KeepAspectRatio)
        

    def updateText(self, texts):
        """
        更新listwidget文本内容
        """

        self.textList.clear()
        for text in texts:
            item = QListWidgetItem(self.textList)
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            item.setText(text)
            item
            item.setCheckState(Qt.CheckState.Unchecked)
            self.textList.indexFromItem
            self.textList.addItem(item)

    def handleItemChanged(self,item):

        any_checked = any(item.checkState() == Qt.Checked for i in range(self.textList.count()) for item in [self.textList.item(i)])
        self.patchCheckedButton.setVisible(any_checked)

    def clear_images(self):
        self.dropCover.show()
        self.textList.clear()   
        self.upload_file = None 
        self.viewer.picScene.clear()
        self.patchedState = False
        self.saveornot.emit(False)
        self.switchButton.setChecked(False)
        self.switchButton.setEnabled(False)
        self.evaluatedState = False
        self.alreadyPatched = False

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
            content=self.tr('Image cleared'),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self
        )
        
    
    def display_image(self, model='paddleocr'):

        self.evaluate(model = model)
        self.patchCheckedButton.setVisible(False)

        self.viewer.scale_factor = 1.0


    
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
        self.show_result(item)



    def apply_patch(self, strength, style):
        if not self.alreadyPatched:
            self.selectRects = []
        
        if self.upload_file == None:
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
        
        for i in range(self.textList.count()):
            item = self.textList.item(i)
            if item.checkState() == Qt.Checked:
                #将currentRecognitions中的列表中的数都转为整数
                bbox =  self.currentRecognitions[self.textList.row(item)]
                for coordinate in bbox:
                    for i in range(len(coordinate)):
                        coordinate[i] = int(coordinate[i])
                self.selectRects.append(bbox)
        
    
        self.stateTooltip = StateToolTip(
            self.tr('Patching'), self.tr('Please wait'), self.window())
        self.stateTooltip.move(self.stateTooltip.getSuitablePos())
        self.stateTooltip.show()
        self.progressCover.progressRing.setValue(0)
        QTimer.singleShot(200, self.progressCover.show) 
        self.progressCover.raise_()

        self.thread = PatchThread(self.upload_file, strength, style, True, self.selectRects, base_path=self.base_path)
        self.thread.progressPartUpdated.connect(self.progressCover.progressRing.setValue)  # 连接进度更新信号
        self.thread.patchPartCompleted.connect(self.show_patch)  # 连接补丁完成信号
        self.thread.start()
    
    def show_patch(self, patched_img_path):

        self.textList.clear()
        self.viewer.picScene.clear()
        self.viewer.picScene.addPixmap(QPixmap(patched_img_path))
        self.viewer.scale_factor = 1.0
        self.update_list_height()
        self.progressCover.hide()
        self.stateTooltip.setContent(
            self.tr('Patch application completed!') + ' 😆')
        self.stateTooltip.setState(True)
        self.saveornot.emit(True)
        QTimer.singleShot(1000, self.enableButtons.emit)
        self.patchCheckedButton.setVisible(False)
        self.alreadyPatched = True
        self.patchedState = True
        

    
    def evaluate(self, model):
        if self.upload_file == None:
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
        self.stateTooltip = StateToolTip(
            self.tr('Evaluating'), self.tr('Please wait'), self.window())
        self.stateTooltip.move(self.stateTooltip.getSuitablePos())
        self.stateTooltip.show()
        self.progressCover.progressRing.setValue(0)
        QTimer.singleShot(200, self.progressCover.show) 
        self.progressCover.raise_()

        if self.alreadyPatched:
            patched_files = [os.path.join(self.patched_dir, file) for file in os.listdir(self.patched_dir)]   
            self.thread = EvaluateThread(self.upload_file, patched_files, model, is_Patch=True, is_Part=True, base_path=self.base_path)
        else:
            self.thread = EvaluateThread(self.upload_file, None, model, is_Patch=False, is_Part=False, base_path=self.base_path)
        
        self.thread.progressPartUpdated.connect(self.progressCover.progressRing.setValue)
        self.thread.evaluatePartCompleted.connect(self.show_result)  # 连接补丁完成信号
        self.thread.start()

    def show_result(self, result):
        if self.alreadyPatched:
            self.viewer.scale_factor = 1.0
            upload_image_result = result[0]["ocr_result_clean"]
            patched_image_result = result[0]["ocr_result_full"]

            self.patchedState = True

            bboxs = patched_image_result["bbox"]
            texts = patched_image_result["texts"]

            self.updateView(bboxs, self.patched_dir+'/'+result[0]["image_name"])
            self.updateText(texts)

            self.show_OCR(result[0])
            self.ocrResultExpand.emit(True)

        else:
            bboxs = result["ocr_result_clean"]["bbox"]
            texts = result["ocr_result_clean"]["texts"]
            self.updateView(bboxs, self.upload_file)
            self.updateText(texts)

        self.textList.setCurrentRow(0)
        self.update_list_height()
        QTimer.singleShot(1000, self.progressCover.hide)
        self.stateTooltip.setContent(
            self.tr('Evaluation completed!') + ' 😆')
        self.stateTooltip.setState(True)
        QTimer.singleShot(1000, self.enableButtons.emit)
        
    def show_OCR(self,result):
        # 展示当前图像Patch前后OCR识别结果的变化
        original_text = ''
        patched_text = ''
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

    def handle_inital_image(self, image_paths):
        if image_paths:
            if len(image_paths) > 1:
                InfoBar.error(
                    title=self.tr('Error'),
                    content=self.tr('Only one image can be uploaded'),
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=3000,
                    parent=self
                )
                return
            self.upload_file = image_paths[0]
            self.display_image('paddleocr')
            QTimer.singleShot(500, lambda:self.dropCover.hide())


class ProtectArea(QWidget):
    applyPatch = Signal(int, int)
    evaluate = Signal(str)
    disableButtons = Signal()
    
    def __init__(self, parent=None, base_path=None):
        super().__init__(parent=parent)
        self.setObjectName('protectArea')
        self.base_path = base_path

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

        self.patchConfirmButton = PrimaryPushButton( self.tr('Add Patch to Selected Area'), self)

        self.modelLabel = QLabel(self.tr('Select Model'), self)
        self.modelButton = ComboBox(self)

        self.evaluateConfirmButton = PrimaryPushButton(self.tr('Evaluate'), self)

        self.modelInfoArea = QFrame(self)
        self.modelInfoLayout = QHBoxLayout(self.modelInfoArea)

        self.__initWidget()

    def __initWidget(self):
        self.initLayout()

        self.strenthButton.addItems([
            '25%',
            '50%',
            '75%',
            '100%'
        ])

        self.styleButton.addItems([
            self.styleButton.addItems([
            self.tr('Generic Patch')+'1',
            self.tr('Generic Patch')+'2',
            self.tr('Generic Patch')+'3'
        ])
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


    def updatePreview(self):
        self.strength = self.strenthButton.currentText()
        style = self.styleButton.currentText()[-1]

        strength_map = {
            '100%': 100,
            '75%': 75,
            '50%': 50,
            '25%': 25,
        }


        self.file_suffix = strength_map[self.strength]
        file_path = f":/gallery/images/patches/advpatch{style}_{self.file_suffix}.png"

        pixmap = QPixmap(file_path)
        self.previewPatch.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio))
    
    def emitApplyPatchSignal(self):
        # 触发 applyPatch 信号的逻辑
        self.disableButtons.emit()
        patch_strength = self.file_suffix
        patch_style = int(self.styleButton.currentText()[-1])
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

        self.ocrText1.setMarkdown(ocr_result[0])
        self.ocrText2.setMarkdown(ocr_result[1])

    def export_result(self, text, type):
        # Function to save the text to a file
        options = QFileDialog.Options()
        fileName, _ = QFileDialog.getSaveFileName(self, f"Save OCR Results - {type}", "", "Text Files (*.txt);;All Files (*)", options=options)
        if fileName:
            with open(fileName, 'w', encoding='utf-8') as file:
                file.write(text)
        

class CustomMessageBox(MessageBoxBase):
    """ Custom message box """

    def __init__(self, parent=None, base_path=None):
        super().__init__(parent)
        self.patched_dir = os.path.join(base_path, 'results/patched_image_part')
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
            'jpg',
            'png',
            '使用原图格式'
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

class PatchPartPage(ScrollArea):

    def __init__(self, parent=None, base_path=None):
        super().__init__(parent=parent)

        self.view = QWidget(self)
        self.vBoxLayout = QVBoxLayout(self.view)
        self.visualizationArea = VisualizationArea(self, base_path=base_path)
        self.ocrResultsArea = OCRResultsArea(self)
        self.protectionArea = ProtectArea(self, base_path=base_path)   

        self.__initWidget()
    
    def __initWidget(self):
        self.initLayout()
        self.view.setObjectName('view')
        self.setObjectName('patchPartPage')
        StyleSheet.PATCH_PART_PAGE.apply(self)

        # self.chartArea.setMaximumHeight(0)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setWidget(self.view)
        self.setWidgetResizable(True)


        self.connectSignalToSlot()

    def connectSignalToSlot(self):

        self.protectionArea.applyPatch.connect(self.visualizationArea.apply_patch)
        self.protectionArea.evaluate.connect(self.visualizationArea.evaluate)

        self.visualizationArea.enableButtons.connect(self.protectionArea.enableUI)
        self.visualizationArea.saveornot.connect(self.protectionArea.savePatchButton.setEnabled)
        self.visualizationArea.applyPatch.connect(self.protectionArea.emitApplyPatchSignal)
        self.visualizationArea.ocrResultExpand.connect(self.ocrresults_show)
        self.visualizationArea.ocrResult.connect(self.ocrResultsArea.show_result)

        signalBus.initialImageSignal_part.connect(self.visualizationArea.handle_inital_image)
        

    def initLayout(self):
        
        self.vBoxLayout.addSpacing(10)
        self.visualizationArea.setFixedHeight(425)
        self.visualizationArea.dropCover.setStyleSheet(f'''
            padding: {self.visualizationArea.height()//4}px;
        ''')
        self.vBoxLayout.addWidget(self.visualizationArea, 1, Qt.AlignTop)
        self.vBoxLayout.addWidget(self.ocrResultsArea, 0, Qt.AlignTop)
        self.vBoxLayout.addSpacing(10)
        self.vBoxLayout.addWidget(self.protectionArea, 0, Qt.AlignTop)
        self.vBoxLayout.addSpacing(10)


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
