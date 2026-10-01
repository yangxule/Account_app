"""「记一笔」页面：选收支类型、填金额、分类、日期、备注，保存到数据库，并显示当日明细。"""

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from account_app import db
from account_app.ui.budget_page import budget_warning_for


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
        # 收支类型：支出 / 收入 单选开关
        self.kind_expense = QRadioButton("支出")
        self.kind_income = QRadioButton("收入")
        self.kind_expense.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.kind_expense)
        group.addButton(self.kind_income)
        self.kind_expense.toggled.connect(self._on_kind_changed)
        kind_row = QHBoxLayout()
        kind_row.addWidget(self.kind_expense)
        kind_row.addWidget(self.kind_income)
        kind_row.addStretch()
        kind_widget = QWidget()
        kind_widget.setLayout(kind_row)

        # 金额：数字输入框，自动带 ¥ 符号，精确到分
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setPrefix("¥ ")
        self.amount_input.setRange(0.0, 999_999.99)
        self.amount_input.setDecimals(2)

        # 分类：两级联动下拉框（先选大类，小类跟着变；随收支类型切换）
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
        form.addRow("类型", kind_widget)
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

        # 当日明细表（只读，跟着日期走；收入显示绿色 + 号）
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

    def _kind(self) -> str:
        """当前选中的收支类型。"""
        return "income" if self.kind_income.isChecked() else "expense"

    def _on_kind_changed(self) -> None:
        """切换支出/收入时，分类下拉框换成对应的一组。"""
        self._load_categories()

    def _load_categories(self) -> None:
        """按当前收支类型加载分类到两个下拉框。"""
        self.top_cat.clear()
        self.sub_cat.clear()
        for cat in db.get_top_categories(self._kind()):
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
            self._show_feedback("请先填写金额", color="#c62828")
            return
        sub_id = self.sub_cat.currentData()
        if sub_id is None:
            self._show_feedback("请选择分类", color="#c62828")
            return
        kind = self._kind()
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        note = self.note_input.text().strip()
        db.insert_expense(
            amount_cents=round(amount * 100),
            category_id=sub_id,
            date=date_str,
            note=note,
            kind=kind,
        )
        kind_text = "收入" if kind == "income" else "支出"
        # 记支出时检查本月预算：接近或超支要提醒
        warn_text, warn_color = None, None
        if kind == "expense":
            month = date_str[:7]
            spent = db.get_month_summary(month)["expense_cents"]
            warn_text, warn_color = budget_warning_for(month, spent)
        if warn_text:
            self._show_feedback(
                f"✓ 已记下 {kind_text}·{self.sub_cat.currentText()} ¥{amount:.2f}\n{warn_text}",
                color=warn_color,
            )
        else:
            self._show_feedback(f"✓ 已记下 {kind_text}·{self.sub_cat.currentText()} ¥{amount:.2f}")
        # 金额和备注清空、类型/分类/日期保留，方便连续记账
        self.amount_input.setValue(0.0)
        self.note_input.clear()
        self.amount_input.setFocus()
        self._refresh_list()
        self.saved.emit()  # 通知明细页等刷新

    def _show_feedback(self, text: str, color: str = "#2e7d32") -> None:
        self.feedback.setStyleSheet(f"color: {color};")
        self.feedback.setText(text)

    # ---------- 当日明细 ----------

    def _refresh_list(self) -> None:
        """按当前所选日期刷新右侧明细表。"""
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        rows = db.get_expenses_by_date(date_str)
        self.today_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            cents = row["amount_cents"]
            is_income = row["kind"] == "income"
            cat_text = f"{row['top_name']} · {row['sub_name']}"
            self.today_table.setItem(i, 0, QTableWidgetItem(cat_text))
            sign = "+" if is_income else ""
            amount_item = QTableWidgetItem(f"{sign}¥{cents / 100:,.2f}")
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            if is_income:
                amount_item.setForeground(QColor("#2e7d32"))  # 收入显示绿色
            self.today_table.setItem(i, 1, amount_item)
            self.today_table.setItem(i, 2, QTableWidgetItem(row["note"]))
