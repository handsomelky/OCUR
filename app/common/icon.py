# coding: utf-8
from enum import Enum

from qfluentwidgets import FluentIconBase, getIconColor, Theme


class Icon(FluentIconBase, Enum):

    DATASHARING = "DataSharing"
    EMOJI_TAB_SYMBOLS = "EmojiTabSymbols"
    FACE = "Face"
    GRID = "Grid"
    MENU = "Menu"
    METADATA_CLEAN = "MetadataClean"
    MODEL_TRAIN = "ModelTrain"
    MOSAIC = "Mosaic"
    NETWORK = "Network"
    PATCH_LIBRARY = "PatchLibrary"
    PORT = "Port"
    PRICE = "Price"
    TEXT = "Text"
    TEXT_HIDE = "TextHide"
    FULL_SCREEN = "FullScreen"
    UPLOAD_IMAGE = "UploadImage"
    TRUSH = "Trush"
    
    

    def path(self, theme=Theme.AUTO):
        return f":/gallery/images/icons/{self.value}_{getIconColor(theme)}.svg"
