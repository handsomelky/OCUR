# coding: utf-8
from enum import Enum

from qfluentwidgets import StyleSheetBase, Theme, isDarkTheme, qconfig


class StyleSheet(StyleSheetBase, Enum):
    """ Style sheet  """

    LINK_CARD = "link_card"
    SAMPLE_CARD = "sample_card"
    SETTING_INTERFACE = "setting_interface"
    PATCH_ALL_PAGE = "patch_all_page"
    PATCH_MANAGER_PAGE = "patch_manager_page"
    PATCH_PART_PAGE = "patch_part_page"
    HOME_PAGE = "home_interface"

    def path(self, theme=Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme
        return f":/gallery/qss/{theme.value.lower()}/{self.value}.qss"
