"""编辑账目的小窗口：字段和「记一笔」一样，改完点保存。"""

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from account_app import db


class ExpenseDialog(QDialog):
    def __init__(self, expense_id: int, parent=None):
        super().__init__(parent)
        self.expense_id = expense_id
        self.setWindowTitle("编辑这笔账")
        self.setMinimumWidth(360)

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

    def _load(self) -> None:
        """回填这笔账的现有内容。"""
        row = db.get_expense(self.expense_id)
        for cat in db.get_top_categories():
            self.top_cat.addItem(cat["name"], cat["id"])
        # 选中这笔账所属的大类 → 触发联动，加载它的小类
        parent_id = db.get_parent_id(row["category_id"])
        idx = self.top_cat.findData(parent_id)
        self.top_cat.setCurrentIndex(max(idx, 0))
        sub_idx = self.sub_cat.findData(row["category_id"])
        self.sub_cat.setCurrentIndex(max(sub_idx, 0))
        self.amount_input.setValue(row["amount_cents"] / 100)
        self.date_input.setDate(QDate.fromString(row["date"], "yyyy-MM-dd"))
        self.note_input.setText(row["note"])

    def _on_top_changed(self) -> None:
        """一级大类变化时，刷新二级小类列表。"""
        top_id = self.top_cat.currentData()
        self.sub_cat.clear()
        for cat in db.get_sub_categories(top_id):
            self.sub_cat.addItem(cat["name"], cat["id"])

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
        )
        self.accept()
