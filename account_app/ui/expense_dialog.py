"""编辑账目的小窗口：字段和「记一笔」一样，改完点保存。"""

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from account_app import db


class ExpenseDialog(QDialog):
    def __init__(self, expense_id: int, parent=None):
        super().__init__(parent)
        self.expense_id = expense_id
        self.setWindowTitle("编辑这笔账")
        self.setMinimumWidth(360)

        # 收支类型开关
        self.kind_expense = QRadioButton("支出")
        self.kind_income = QRadioButton("收入")
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

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setPrefix("¥ ")
        self.amount_input.setRange(0.01, 999_999.99)
        self.amount_input.setDecimals(2)

        self.top_cat = QComboBox()
        self.sub_cat = QComboBox()
        self.top_cat.currentIndexChanged.connect(self._on_top_changed)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("yyyy-MM-dd")

        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("备注（可留空）")

        form = QFormLayout()
        form.addRow("类型", kind_widget)
        form.addRow("金额", self.amount_input)
        form.addRow("分类", self.top_cat)
        form.addRow("", self.sub_cat)
        form.addRow("日期", self.date_input)
        form.addRow("备注", self.note_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._load()

    def _kind(self) -> str:
        """当前选中的收支类型。"""
        return "income" if self.kind_income.isChecked() else "expense"

    def _load(self) -> None:
        """回填这笔账的现有内容。"""
        row = db.get_expense(self.expense_id)
        # 先按这笔账的收支类型选中开关，再加载对应分类
        if row["kind"] == "income":
            self.kind_income.setChecked(True)
        self._load_categories()
        # 选中这笔账所属的大类 → 触发联动，加载它的小类
        parent_id = db.get_parent_id(row["category_id"])
        idx = self.top_cat.findData(parent_id)
        self.top_cat.setCurrentIndex(max(idx, 0))
        sub_idx = self.sub_cat.findData(row["category_id"])
        self.sub_cat.setCurrentIndex(max(sub_idx, 0))
        self.amount_input.setValue(row["amount_cents"] / 100)
        self.date_input.setDate(QDate.fromString(row["date"], "yyyy-MM-dd"))
        self.note_input.setText(row["note"])

    def _on_kind_changed(self) -> None:
        """切换支出/收入时，分类下拉框换成对应的一组。"""
        self._load_categories()

    def _load_categories(self) -> None:
        """按当前收支类型加载分类到两个下拉框（带图标显示）。"""
        self.top_cat.clear()
        self.sub_cat.clear()
        for cat in db.get_top_categories(self._kind()):
            self.top_cat.addItem(self._cat_label(cat), cat["id"])
        self._on_top_changed()  # 联动刷新二级分类

    def _on_top_changed(self) -> None:
        """一级大类变化时，刷新二级小类列表。"""
        top_id = self.top_cat.currentData()
        self.sub_cat.clear()
        for cat in db.get_sub_categories(top_id):
            self.sub_cat.addItem(self._cat_label(cat), cat["id"])

    @staticmethod
    def _cat_label(cat) -> str:
        """「图标 + 空格 + 名字」的显示文本（无图标时只有名字）。"""
        icon = cat["icon"] or ""
        return f"{icon} {cat['name']}" if icon else cat["name"]

    def _on_save(self) -> None:
        amount = self.amount_input.value()
        if amount <= 0 or self.sub_cat.currentData() is None:
            return  # 正常情况下到不了这里（金额下限 0.01，分类必有选项）
        db.update_expense(
            self.expense_id,
            amount_cents=round(amount * 100),
            category_id=self.sub_cat.currentData(),
            date=self.date_input.date().toString("yyyy-MM-dd"),
            note=self.note_input.text().strip(),
            kind=self._kind(),
        )
        self.accept()
