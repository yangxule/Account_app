"""「明细」页面：全部账目列表 + 搜索筛选。功能下一步开发。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ExpenseList(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("「明细」开发中…\n\n这里将显示：全部账目列表，支持搜索和筛选")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
