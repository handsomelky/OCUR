import random
import math
from PySide6.QtWidgets import QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem, QGraphicsPolygonItem, QGraphicsSceneHoverEvent, QGraphicsSceneMouseEvent, QStyle
from PySide6.QtGui import QPixmap, QPolygon, QPen, QColor, QBrush
from PySide6.QtCore import QPoint, Qt

from qfluentwidgets import ListWidget

class GraphScene(QGraphicsScene):
    """
    图像管理场景
    """
    def __init__(self):
        super().__init__()

class GraphicsPolygonItem(QGraphicsPolygonItem):
    """
    框图元
    """
    def __init__(self, points, index, parent, textList):
        super().__init__()
        # 识别结果的id
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

            # self.signal.emit(self.index)
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
