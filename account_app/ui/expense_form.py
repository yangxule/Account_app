"""「记一笔」页面：填写金额、分类、日期、备注并保存。功能下一步开发。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ExpenseForm(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel("「记一笔」开发中…\n\n这里将显示：金额输入框、分类选择、日期、备注、保存按钮")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
