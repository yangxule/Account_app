"""全局皮肤（QSS）：清新绿主题，统一所有页面的配色与控件外观。

配色方案：
- 主绿 #43a047（悬停 #388e3c / 按下 #2e7d32），与收入显示用的绿色呼应
- 页面底色 #f4f7f4（带一点绿意的浅灰），卡片/输入框白色，边框 #d7e5d8
- 危险操作红 #e53935（删除按钮）
"""

QSS = """
QWidget {
    font-size: 14px;
    color: #263238;
}

QMainWindow, QDialog {
    background: #f4f7f4;
}

/* ---------- 标签页 ---------- */
QTabWidget::pane {
    background: #ffffff;
    border: 1px solid #d7e5d8;
    border-radius: 8px;
}
QTabBar::tab {
    background: #e6efe6;
    color: #5a6b5a;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #2e7d32;
    font-weight: bold;
}
QTabBar::tab:hover:!selected {
    background: #eef5ee;
}

/* ---------- 按钮 ----------
   注意：按钮必须带实线边框（不能是 none/transparent），
   Qt 才会启用样式表绘制，背景色才生效。 */
QPushButton {
    background: #43a047;
    color: #ffffff;
    border: 1px solid #43a047;
    border-radius: 6px;
    padding: 6px 18px;
}
QPushButton:hover { background: #388e3c; border-color: #388e3c; }
QPushButton:pressed { background: #2e7d32; border-color: #2e7d32; }
QPushButton:disabled { background: #c9d4c9; border-color: #c9d4c9; color: #f5f8f5; }

/* 删除类按钮用红色，与普通绿色按钮区分 */
QPushButton#danger { background: #e53935; border-color: #e53935; }
QPushButton#danger:hover { background: #c62828; border-color: #c62828; }
QPushButton#danger:pressed { background: #b71c1c; border-color: #b71c1c; }

/* 表格行内的编辑/删除按钮小一号，避免撑开行高 */
QTableWidget QPushButton { padding: 3px 12px; font-size: 13px; }

/* ---------- 输入控件 ---------- */
QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit {
    background: #ffffff;
    border: 1px solid #cfe0cf;
    border-radius: 6px;
    padding: 4px 8px;
    min-height: 22px;
}
QLineEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
    border: 1px solid #43a047;
}
QLineEdit:disabled, QComboBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {
    background: #f0f4f0;
    color: #9aa89a;
}
QComboBox::drop-down, QDateEdit::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #cfe0cf;
    selection-background-color: #c8e6c9;
    selection-color: #1b5e20;
}

/* ---------- 表格与分类树 ---------- */
QTableWidget, QTreeWidget {
    background: #ffffff;
    alternate-background-color: #f6faf6;
    border: 1px solid #d7e5d8;
    border-radius: 6px;
    gridline-color: #eaf2ea;
}
QHeaderView::section {
    background: #e6efe6;
    color: #33613a;
    font-weight: bold;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #d7e5d8;
}
QTableWidget::item { padding: 3px; }
QTableWidget::item:selected, QTreeWidget::item:selected {
    background: #c8e6c9;
    color: #1b5e20;
}
QTreeWidget::item { padding: 3px; }

/* ---------- 进度条（预算页会按状态单独覆盖颜色） ---------- */
QProgressBar {
    background: #e6efe6;
    border: none;
    border-radius: 10px;
}
QProgressBar::chunk {
    background-color: #43a047;
    border-radius: 10px;
}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #c9d8c9;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #a9c0a9; }
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #c9d8c9;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #a9c0a9; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }

/* ---------- 白色圆角卡片（统计页数字卡片 / 图表容器） ---------- */
QFrame#statCard {
    background: #ffffff;
    border: 1px solid #d7e5d8;
    border-radius: 10px;
}
"""


def apply(app) -> None:
    """把皮肤应用到整个 App（在创建窗口前调用一次）。"""
    app.setStyleSheet(QSS)
