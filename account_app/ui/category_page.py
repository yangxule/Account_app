"""「分类设置」页面：两级分类的增删改。功能下一步开发。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CategoryPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("「分类设置」开发中…\n\n这里将显示：分类树，支持增删改")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
