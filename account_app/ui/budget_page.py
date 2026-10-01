"""「预算」页面：设置月度预算与提醒。功能下一步开发。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class BudgetPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("「预算」开发中…\n\n这里将显示：月度预算设置，快花超时提醒")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
