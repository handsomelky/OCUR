import random
import math
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem, QGraphicsPolygonItem, QGraphicsView,QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent, QStyle, QGraphicsRectItem
from PySide6.QtGui import QPixmap, QPolygon, QPen, QColor, QMouseEvent
from PySide6.QtCore import QPoint, Qt, QRectF

from qfluentwidgets import ListWidget
from ..common.signal_bus import signalBus

class GraphScene(QGraphicsScene):
    """
    图像管理场景
    """
    def __init__(self):
        super().__init__()

    
class GraphicsView(QGraphicsView):

    def __init__(self, scene, parent):
        super().__init__()

        self.selectionMode = False
        self.clearMode = False  # 新增一个清除模式标志
        self.rectangles = []  # 用于存储所有矩形
        self.startPoint = None
        self.currentRect = None
        self.picScene = scene

        self.BOX_COLORS = [(82, 85, 255), (255, 130, 80), (240, 70, 255), (255, 255, 19), (30, 255, 30)]
        

    def set_selection_mode(self, enabled):
        self.selectionMode = enabled

    def set_clear_mode(self, enabled):
        self.clearMode = enabled

    def mousePressEvent(self, event: QMouseEvent):   
        if self.selectionMode and event.button() == Qt.MouseButton.LeftButton:
            if not self.currentRect:
                self.startPoint = self.mapToScene(event.pos())
                self.currentRect = QGraphicsRectItem()
                self.color = random.choices(self.BOX_COLORS)[0]
                self.currentRect.setPen(QPen(QColor(*self.color), 1))
                self.currentRect.setBrush(QColor(*self.color, 127))
                self.picScene.addItem(self.currentRect)
            else:
                self.rectangles.append(self.currentRect)
                self.currentRect = None
        if self.clearMode and event.button() == Qt.MouseButton.LeftButton:
            # 清除点击的矩形
            for rect in self.rectangles:
                if rect.rect().contains(self.mapToScene(event.pos())):
                    self.picScene.removeItem(rect)
                    self.rectangles.remove(rect)
                    break

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.selectionMode and self.currentRect:
            endPoint = self.mapToScene(event.pos())
            rect = QRectF(self.startPoint, endPoint).normalized()
            self.currentRect.setRect(rect)
        super().mouseMoveEvent(event)
        

class GraphicsPolygonItem(QGraphicsPolygonItem):
    """
    框图元
    """
    def __init__(self, points, index, parent, textList):
        super().__init__()
        # 识别结果的id
        self.parent = parent
        self.chosen = False
        self.index = index
        self.setAcceptHoverEvents(True)  # 启用悬停事件
        self.BOX_COLORS = [(82, 85, 255), (255, 130, 80), (240, 70, 255), (255, 255, 19), (30, 255, 30)]
        self.color = random.choices(self.BOX_COLORS)[0]
        self.points = points
        self.textList = textList
        self.setPen(QPen(QColor(*self.color), 1))
        # 画框
        self.polygon = QPolygon()
        for point in points:
            self.polygon.append(QPoint(point[0], point[1]))
        self.setPolygon(self.polygon)
        # 设置可以选择
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        parent.addItem(self)
    
    def hoverEnterEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.setBrush(QColor(*self.color, 127))
        self.setPen(QPen(QColor(*self.color), 1))
        # 取消默认的虚线
        self.state = QStyle.State_None
        self.textList.scrollToItem(self.textList.item(self.index), ListWidget.ScrollHint.PositionAtCenter)
        self.textList.setCurrentRow(self.index)
        return super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event: QGraphicsSceneHoverEvent) -> None:
        self.setBrush(QColor(0, 0, 0, 0))
        self.setPen(QPen(QColor(*self.color), 1))
        return super().hoverLeaveEvent(event)
    
    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        if self.isSelected():
            self.textList.item(self.index).setCheckState(Qt.CheckState.Checked)

        return super().mouseReleaseEvent(event)

    def set_brush(self, brushed):
        self.chosen = brushed
        signalBus.repaintSignal.emit()


    def paint(self, painter, option, widget):
        # 设置选中样式
        if self.isSelected():
            painter.setBrush(QColor(*self.color, 127))
            painter.setPen(QPen(QColor(*self.color), 1))
            painter.drawPolygon(self.polygon)
            # 取消默认的虚线
            option.state = QStyle.State_None
            self.textList.scrollToItem(self.textList.item(self.index), ListWidget.ScrollHint.PositionAtCenter)
            self.textList.setCurrentRow(self.index)
        
        if self.chosen:
            painter.setBrush(QColor(*self.color, 127))
            # 设置虚线样式， 间隔大一些
            painter.setPen(QPen(QColor(*self.color), 1))
            painter.drawPolygon(self.polygon)
        super().paint(painter, option, widget)
    
class GraphicsImageItem(QGraphicsPixmapItem):
    """
    照片图源
    """
    def __init__(self, path, parent):
        super().__init__()
        self.pix = QPixmap(path)
        # 设置图元
        self.setPixmap(self.pix)
        # 加入图元
        parent.addItem(self)

    

    
