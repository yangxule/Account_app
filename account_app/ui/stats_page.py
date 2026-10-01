"""「统计」页面：饼图、趋势图等统计图表。功能下一步开发。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class StatsPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("「统计」开发中…\n\n这里将显示：月度总支出、分类占比饼图、花费趋势图")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
