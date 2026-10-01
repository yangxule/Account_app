"""「预算」页面：设置每月预算，显示本月进度与状态。"""

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from account_app import db

# 提醒阈值：花到预算的 80% 算「接近预算」
WARN_RATIO = 0.8


class BudgetPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load()
        self.refresh()

    # ---------- 界面搭建 ----------

    def _build_ui(self) -> None:
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setPrefix("¥ ")
        self.amount_input.setRange(0.0, 9_999_999.99)
        self.amount_input.setDecimals(2)
        self.amount_input.setSpecialValueText("未设置")
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self._save)

        self.feedback = QLabel("")

        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("每月预算"))
        input_row.addWidget(self.amount_input)
        input_row.addWidget(self.save_btn)
        input_row.addStretch()

        self.month_label = QLabel("")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(22)
        self.detail = QLabel("")
        self.status = QLabel("")

        rule = QLabel("提醒规则：本月支出花到预算的 80% 时提醒「接近预算」；超过 100% 时提醒「已超支」。")
        rule.setStyleSheet("color: #666;")
        rule.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addLayout(input_row)
        layout.addWidget(self.feedback)
        layout.addWidget(self.month_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.detail)
        layout.addWidget(self.status)
        layout.addStretch()
        layout.addWidget(rule)

    # ---------- 数据 ----------

    def _load(self) -> None:
        """回填已保存的预算。"""
        raw = db.get_setting("monthly_budget")
        if raw:
            self.amount_input.setValue(int(raw) / 100)

    def _save(self) -> None:
        value = self.amount_input.value()
        db.set_setting("monthly_budget", str(round(value * 100)))
        self.refresh()
        if value <= 0:
            self.feedback.setText("✓ 已停用预算提醒")
        else:
            self.feedback.setText(f"✓ 每月预算已设为 ¥{value:,.2f}")
        self.feedback.setStyleSheet("color: #2e7d32;")

    def refresh(self) -> None:
        """刷新本月进度条和状态。"""
        month = datetime.now().strftime("%Y-%m")
        self.month_label.setText(f"本月进度（{month}）")
        spent = db.get_month_summary(month)["expense_cents"] / 100
        raw = db.get_setting("monthly_budget")
        if not raw or int(raw) <= 0:
            self.progress.setValue(0)
            self.progress.setStyleSheet("QProgressBar::chunk { background-color: #bdbdbd; }")
            self.detail.setText(f"本月已花 ¥{spent:,.2f}（尚未设置预算）")
            self.status.setText("状态：未设置预算")
            self.status.setStyleSheet("color: #666;")
            return
        budget = int(raw) / 100
        pct = spent / budget * 100
        self.progress.setValue(min(100, int(pct)))
        if pct >= 100:
            color = "#c62828"
            self.status.setText("状态：已超支！")
            self.status.setStyleSheet(f"color: {color}; font-weight: bold;")
        elif pct >= WARN_RATIO * 100:
            color = "#ef6c00"
            self.status.setText("状态：接近预算")
            self.status.setStyleSheet(f"color: {color}; font-weight: bold;")
        else:
            color = "#2e7d32"
            self.status.setText("状态：正常")
            self.status.setStyleSheet(f"color: {color};")
        self.progress.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; }}")
        self.detail.setText(f"已花 ¥{spent:,.2f} / 预算 ¥{budget:,.2f}（{pct:.1f}%）")


def budget_warning_for(month: str, spent_cents: int) -> tuple[str | None, str | None]:
    """记账时用的预算提醒：返回 (提醒文字, 颜色)。没设预算或没到阈值返回 (None, None)。"""
    raw = db.get_setting("monthly_budget")
    if not raw:
        return None, None
    budget_cents = int(raw)
    if budget_cents <= 0:
        return None, None
    if spent_cents >= budget_cents:
        return (
            f"⚠ 本月已花 ¥{spent_cents / 100:,.2f}，已超出预算 ¥{budget_cents / 100:,.2f}！",
            "#c62828",
        )
    if spent_cents >= budget_cents * WARN_RATIO:
        pct = spent_cents / budget_cents * 100
        return (f"⚠ 本月已花掉预算的 {pct:.0f}%，接近预算上限", "#ef6c00")
    return None, None
