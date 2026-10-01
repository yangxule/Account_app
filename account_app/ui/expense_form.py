"""「记一笔」页面：填写金额、分类、日期、备注，保存到数据库，并显示当日明细。"""

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from account_app import db


class ExpenseForm(QWidget):
    # 保存成功后发出，供其他页面（如明细页）刷新
    saved = Signal()

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load_categories()
        self._refresh_list()

    # ---------- 界面搭建 ----------

    def _build_ui(self) -> None:
        # 金额：数字输入框，自动带 ¥ 符号，精确到分
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setPrefix("¥ ")
        self.amount_input.setRange(0.0, 999_999.99)
        self.amount_input.setDecimals(2)

        # 分类：两级联动下拉框（先选大类，小类跟着变）
        self.top_cat = QComboBox()
        self.sub_cat = QComboBox()
        self.top_cat.currentIndexChanged.connect(self._on_top_changed)

        # 日期：默认今天，点开是日历；改日期时右侧明细跟着变
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")
        self.date_input.dateChanged.connect(self._refresh_list)

        # 备注（可留空）
        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("备注（可留空）")

        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save)

        # 保存结果提示（绿色=成功，红色=出错）
        self.feedback = QLabel("")
        self.feedback.setStyleSheet("color: #2e7d32;")

        form = QFormLayout()
        form.addRow("金额", self.amount_input)
        form.addRow("分类", self.top_cat)
        form.addRow("", self.sub_cat)
        form.addRow("日期", self.date_input)
        form.addRow("备注", self.note_input)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.save_btn)
        btn_row.addStretch()

        left = QVBoxLayout()
        left.addLayout(form)
        left.addLayout(btn_row)
        left.addWidget(self.feedback)
        left.addStretch()

        # 当日明细表（只读，跟着日期走）
        self.today_table = QTableWidget(0, 3)
        self.today_table.setHorizontalHeaderLabels(["分类", "金额", "备注"])
        self.today_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.today_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.today_table.horizontalHeader().setStretchLastSection(True)
        self.today_table.setColumnWidth(0, 150)
        self.today_table.setColumnWidth(1, 100)

        right = QVBoxLayout()
        right.addWidget(QLabel("当日明细"))
        right.addWidget(self.today_table)

        main = QHBoxLayout(self)
        main.addLayout(left, 2)
        main.addLayout(right, 3)

    # ---------- 数据加载 ----------

    def _load_categories(self) -> None:
        """把分类加载到两个下拉框。"""
        for cat in db.get_top_categories():
            self.top_cat.addItem(cat["name"], cat["id"])
        self._on_top_changed()  # 联动刷新二级分类

    def _on_top_changed(self) -> None:
        """一级大类变化时，刷新二级小类列表。"""
        top_id = self.top_cat.currentData()
        self.sub_cat.clear()
        for cat in db.get_sub_categories(top_id):
            self.sub_cat.addItem(cat["name"], cat["id"])

    # ---------- 保存 ----------

    def _save(self) -> None:
        amount = self.amount_input.value()
        if amount <= 0:
            self._show_feedback("请先填写金额", ok=False)
            return
        sub_id = self.sub_cat.currentData()
        if sub_id is None:
            self._show_feedback("请选择分类", ok=False)
            return
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        note = self.note_input.text().strip()
        db.insert_expense(
            amount_cents=round(amount * 100),
            category_id=sub_id,
            date=date_str,
            note=note,
        )
        self._show_feedback(f"✓ 已记下 {self.sub_cat.currentText()} ¥{amount:.2f}")
        # 金额和备注清空、分类和日期保留，方便连续记账
        self.amount_input.setValue(0.0)
        self.note_input.clear()
        self.amount_input.setFocus()
        self._refresh_list()
        self.saved.emit()  # 通知明细页等刷新

    def _show_feedback(self, text: str, ok: bool = True) -> None:
        self.feedback.setStyleSheet("color: #2e7d32;" if ok else "color: #c62828;")
        self.feedback.setText(text)

    # ---------- 当日明细 ----------

    def _refresh_list(self) -> None:
        """按当前所选日期刷新右侧明细表。"""
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        rows = db.get_expenses_by_date(date_str)
        self.today_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            cents = row["amount_cents"]
            cat_text = f"{row['top_name']} · {row['sub_name']}"
            self.today_table.setItem(i, 0, QTableWidgetItem(cat_text))
            amount_item = QTableWidgetItem(f"¥{cents / 100:.2f}")
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.today_table.setItem(i, 1, amount_item)
            self.today_table.setItem(i, 2, QTableWidgetItem(row["note"]))
