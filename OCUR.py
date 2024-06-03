# coding:utf-8
import os
import sys

from PySide6.QtCore import Qt, QTranslator, QLoggingCategory
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from qfluentwidgets import FluentTranslator

from app.common.signal_bus import signalBus

import shutil



from app.common.config import cfg
from app.view.main_window import MainWindow

def get_base_path():
    """获取可执行文件所在的目录"""
    if len(sys.argv) > 1:
        soft_path = sys.argv[0]
        return os.path.dirname(soft_path)
    if getattr(sys, 'frozen', False):
        # 如果程序是被冻结的（即打包后执行），使用可执行文件的目录
        return os.path.dirname(sys.executable)
    else:  
        return os.path.dirname(os.path.abspath(__file__))

base_path = get_base_path()

check_dirs = ['results', 'uploads', 'results/patched_images', 'results/evaluated_upload_images', 'results/evaluated_patched_images', 'results/patched_image_part', 'results/evaluated_upload_image_part', 'results/evaluated_patched_image_part']

for check_dir in check_dirs:
    full_dir = os.path.join(base_path, check_dir)
    if os.path.exists(full_dir):
        shutil.rmtree(full_dir)
    os.makedirs(full_dir)

# enable dpi scale
if cfg.get(cfg.dpiScale) != "Auto":
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_SCALE_FACTOR"] = str(cfg.get(cfg.dpiScale))

# create application
app = QApplication(sys.argv)
app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

mode = sys.argv[1] if len(sys.argv) > 1 else None
image_paths = sys.argv[2:] if len(sys.argv) > 2 else None

# internationalization
locale = cfg.get(cfg.language).value
translator = FluentTranslator(locale)
Translator = QTranslator()
Translator.load(locale, "gallery", ".", ":/gallery/i18n")

app.installTranslator(translator)
app.installTranslator(Translator)

# create main window
w = MainWindow(mode, image_paths, base_path)
w.show()

app.exec()