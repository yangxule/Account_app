"""「明细」页面：全部账目列表，支持实时筛选、编辑、删除、导出。"""

import csv
from datetime import datetime

from openpyxl import Workbook
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from account_app import db
from account_app.config import BASE_DIR
from account_app.ui.expense_dialog import ExpenseDialog

# 导出文件存放文件夹
EXPORT_DIR = BASE_DIR / "exports"


class ExpenseList(QWidget):
    def __init__(self):
        super().__init__()
        self._last_rows: list = []  # 当前筛选结果（导出时用）
        self._build_ui()
        self._load_categories()

    # ---------- 界面搭建 ----------

    def _build_ui(self) -> None:
        # 筛选栏第一行：关键字 + 日期范围
        self.keyword_input = QLineEdit()
        self.keyword_input.setPlaceholderText("🔍 搜备注或分类名")
        self.keyword_input.textChanged.connect(self.refresh)

        self.date_check = QCheckBox("按日期")
        self.date_check.toggled.connect(self._on_date_check)
        self.date_from = QDateEdit(QDate.currentDate())
        self.date_to = QDateEdit(QDate.currentDate())
        for w in (self.date_from, self.date_to):
            w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd")
            w.setEnabled(False)
            w.dateChanged.connect(self.refresh)

        filter_row1 = QHBoxLayout()
        filter_row1.addWidget(self.keyword_input, 2)
        filter_row1.addWidget(self.date_check)
        filter_row1.addWidget(self.date_from)
        filter_row1.addWidget(QLabel("~"))
        filter_row1.addWidget(self.date_to)
        filter_row1.addStretch()

        # 筛选栏第二行：类型 + 分类 + 金额范围 + 重置 + 导出
        self.kind_filter = QComboBox()
        self.kind_filter.addItem("全部", None)
        self.kind_filter.addItem("支出", "expense")
        self.kind_filter.addItem("收入", "income")
        self.kind_filter.currentIndexChanged.connect(self.refresh)

        self.top_filter = QComboBox()
        self.sub_filter = QComboBox()
        self.top_filter.currentIndexChanged.connect(self._on_top_filter_changed)

        self.min_amount = QDoubleSpinBox()
        self.max_amount = QDoubleSpinBox()
        for w in (self.min_amount, self.max_amount):
            w.setPrefix("¥ ")
            w.setRange(0.0, 999_999.99)
            w.setDecimals(2)
            w.setSpecialValueText("不限")
            w.valueChanged.connect(self.refresh)

        self.reset_btn = QPushButton("↺ 重置")
        self.reset_btn.clicked.connect(self._reset_filters)
        self.export_xlsx_btn = QPushButton("📤 导出 Excel")
        self.export_csv_btn = QPushButton("📄 导出 CSV")
        self.export_xlsx_btn.clicked.connect(lambda: self._export("xlsx"))
        self.export_csv_btn.clicked.connect(lambda: self._export("csv"))

        filter_row2 = QHBoxLayout()
        filter_row2.addWidget(QLabel("类型"))
        filter_row2.addWidget(self.kind_filter)
        filter_row2.addWidget(QLabel("分类"))
        filter_row2.addWidget(self.top_filter)
        filter_row2.addWidget(self.sub_filter)
        filter_row2.addWidget(QLabel("金额"))
        filter_row2.addWidget(self.min_amount)
        filter_row2.addWidget(QLabel("~"))
        filter_row2.addWidget(self.max_amount)
        filter_row2.addWidget(self.reset_btn)
        filter_row2.addStretch()
        filter_row2.addWidget(self.export_xlsx_btn)
        filter_row2.addWidget(self.export_csv_btn)

        self.feedback = QLabel("")

        # 明细表（只读）
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["日期", "分类", "金额", "备注", "操作"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)  # 隔行浅色，配合皮肤更易读
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # 备注占满剩余
        self.table.setColumnWidth(0, 110)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(4, 170)

        self.summary = QLabel("")

        layout = QVBoxLayout(self)
        layout.addLayout(filter_row1)
        layout.addLayout(filter_row2)
        layout.addWidget(self.feedback)
        layout.addWidget(self.table)
        layout.addWidget(self.summary)

    # ---------- 筛选 ----------

    def _load_categories(self) -> None:
        self.top_filter.addItem("全部大类", None)
        for cat in db.get_top_categories():
            self.top_filter.addItem(self._cat_label(cat), cat["id"])
        self.sub_filter.addItem("全部小类", None)
        self._on_top_filter_changed()

    def _on_top_filter_changed(self) -> None:
        """大类筛选变化时，刷新小类筛选列表。"""
        top_id = self.top_filter.currentData()
        self.sub_filter.clear()
        self.sub_filter.addItem("全部小类", None)
        if top_id is not None:
            for cat in db.get_sub_categories(top_id):
                self.sub_filter.addItem(self._cat_label(cat), cat["id"])
            self.sub_filter.setEnabled(True)
        else:
            self.sub_filter.setEnabled(False)
        self.refresh()

    @staticmethod
    def _cat_label(cat) -> str:
        """「图标 + 空格 + 名字」的显示文本（无图标时只有名字）。"""
        icon = cat["icon"] or ""
        return f"{icon} {cat['name']}" if icon else cat["name"]

    def _on_date_check(self, checked: bool) -> None:
        self.date_from.setEnabled(checked)
        self.date_to.setEnabled(checked)
        self.refresh()

    def _reset_filters(self) -> None:
        """全部筛选条件恢复默认。"""
        widgets = (
            self.keyword_input, self.date_check, self.date_from, self.date_to,
            self.kind_filter, self.top_filter, self.sub_filter,
            self.min_amount, self.max_amount,
        )
        for w in widgets:
            w.blockSignals(True)  # 重置过程中不触发一次次刷新
        self.keyword_input.clear()
        self.date_check.setChecked(False)
        today = QDate.currentDate()
        self.date_from.setDate(today)
        self.date_to.setDate(today)
        self.kind_filter.setCurrentIndex(0)
        self.top_filter.setCurrentIndex(0)
        self.sub_filter.setCurrentIndex(0)
        self.min_amount.setValue(0.0)
        self.max_amount.setValue(0.0)
        for w in widgets:
            w.blockSignals(False)
        self.refresh()

    def refresh(self) -> None:
        """按当前筛选条件重新查账并刷新表格（筛选改动即生效）。"""
        keyword = self.keyword_input.text().strip()
        use_date = self.date_check.isChecked()
        top_id = self.top_filter.currentData()
        sub_id = self.sub_filter.currentData()
        kind = self.kind_filter.currentData()
        min_cents = round(self.min_amount.value() * 100) or None
        max_cents = round(self.max_amount.value() * 100) or None
        rows = db.search_expenses(
            keyword=keyword,
            date_from=self.date_from.date().toString("yyyy-MM-dd") if use_date else "",
            date_to=self.date_to.date().toString("yyyy-MM-dd") if use_date else "",
            top_id=top_id,
            sub_id=sub_id,
            min_cents=min_cents,
            max_cents=max_cents,
            kind=kind,
        )
        self._last_rows = rows
        self._fill_table(rows)
        expense_total = sum(r["amount_cents"] for r in rows if r["kind"] == "expense")
        income_total = sum(r["amount_cents"] for r in rows if r["kind"] == "income")
        self.summary.setText(
            f"共 {len(rows)} 笔 · 支出 ¥{expense_total / 100:,.2f}"
            f" · 收入 ¥{income_total / 100:,.2f}"
        )

    def _fill_table(self, rows) -> None:
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            is_income = row["kind"] == "income"
            top = f"{row['top_icon']} {row['top_name']}".strip()
            sub = f"{row['sub_icon']} {row['sub_name']}".strip()
            self.table.setItem(i, 0, QTableWidgetItem(row["date"]))
            self.table.setItem(i, 1, QTableWidgetItem(f"{top} · {sub}"))
            sign = "+" if is_income else ""
            amount_item = QTableWidgetItem(f"{sign}¥{row['amount_cents'] / 100:,.2f}")
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            if is_income:
                amount_item.setForeground(QColor("#2e7d32"))  # 收入显示绿色 + 号
            self.table.setItem(i, 2, amount_item)
            self.table.setItem(i, 3, QTableWidgetItem(row["note"]))

            # 每行两个操作按钮（删除是危险操作，用红色）
            edit_btn = QPushButton("编辑")
            del_btn = QPushButton("删除")
            del_btn.setObjectName("danger")
            edit_btn.clicked.connect(lambda _, eid=row["id"]: self._edit(eid))
            del_btn.clicked.connect(lambda _, eid=row["id"]: self._delete(eid))
            box = QWidget()
            h = QHBoxLayout(box)
            h.setContentsMargins(2, 2, 2, 2)
            h.addWidget(edit_btn)
            h.addWidget(del_btn)
            self.table.setCellWidget(i, 4, box)

    # ---------- 编辑 / 删除 ----------

    def _edit(self, expense_id: int) -> None:
        dialog = ExpenseDialog(expense_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._show_feedback("✓ 已保存修改")
            self.refresh()

    def _delete(self, expense_id: int) -> None:
        row = db.get_expense(expense_id)
        box = QMessageBox(self)
        box.setWindowTitle("确认删除")
        box.setText(f"确定删除这笔账吗？\n{row['date']}  ¥{row['amount_cents'] / 100:,.2f}")
        yes_btn = box.addButton("删除", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is yes_btn:
            db.delete_expense(expense_id)
            self._show_feedback("✓ 已删除")
            self.refresh()

    # ---------- 导出 ----------

    def _export(self, fmt: str) -> None:
        """把当前筛选结果导出为 CSV 或 Excel 文件，存到 exports/ 文件夹。"""
        rows = self._last_rows
        if not rows:
            self._show_feedback("当前没有可导出的账目", ok=False)
            return
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        headers = ["日期", "类型", "一级分类", "二级分类", "金额(元)", "备注"]
        data_rows = [
            [
                r["date"],
                "收入" if r["kind"] == "income" else "支出",
                r["top_name"],
                r["sub_name"],
                r["amount_cents"] / 100,
                r["note"],
            ]
            for r in rows
        ]
        if fmt == "csv":
            path = EXPORT_DIR / f"账目导出_{stamp}.csv"
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(data_rows)
        else:
            path = EXPORT_DIR / f"账目导出_{stamp}.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.title = "账目"
            ws.append(headers)
            for row in data_rows:
                ws.append(row)
            wb.save(path)
        self._show_feedback(f"✓ 已导出 {len(rows)} 笔到：{path}")

    def _show_feedback(self, text: str, ok: bool = True) -> None:
        self.feedback.setStyleSheet("color: #2e7d32;" if ok else "color: #c62828;")
        self.feedback.setText(text)
