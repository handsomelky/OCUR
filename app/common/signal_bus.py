# coding: utf-8
from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """ Signal bus """

    switchToSampleCard = Signal(str)
    micaEnableChanged = Signal(bool)
    supportSignal = Signal()
    # 传递初始图像参数的信号
    initialImageSignal_part = Signal(list)
    initialImageSignal_full = Signal(list)

signalBus = SignalBus()