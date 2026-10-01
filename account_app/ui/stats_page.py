"""「统计」页面：月度收支卡片、支出分类饼图、近12个月收支趋势柱状图。"""

from datetime import datetime

import matplotlib

matplotlib.use("qtagg")  # 嵌入 Qt 窗口的绘图后端（须在导入 canvas 之前设置）

from matplotlib import font_manager
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from account_app import db


def _setup_chinese_font() -> None:
    """让图表能显示中文：从系统字体里挑一个中文字体。"""
    import matplotlib as mpl

    mpl.rcParams["axes.unicode_minus"] = False
    candidates = [
        "Noto Sans CJK SC",
        "Noto Serif CJK SC",
        "AR PL UMing CN",
        "WenQuanYi Micro Hei",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            mpl.rcParams["font.family"] = [name]
            return
    # 兜底：找任意含中文的字体
    for f in font_manager.fontManager.ttflist:
        if "CJK" in f.name or "UMing" in f.name or "UKai" in f.name:
            mpl.rcParams["font.family"] = [f.name]
            return


_setup_chinese_font()


class StatsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load_months()

    # ---------- 界面搭建 ----------

    def _build_ui(self) -> None:
        # 月份选择
        self.month_combo = QComboBox()
        self.month_combo.currentIndexChanged.connect(self.refresh)
        month_row = QHBoxLayout()
        month_row.addWidget(QLabel("月份"))
        month_row.addWidget(self.month_combo)
        month_row.addStretch()

        # 三张卡片：支出 / 收入 / 结余
        self.card_expense_frame, self.card_expense = self._make_card("支出")
        self.card_income_frame, self.card_income = self._make_card("收入")
        self.card_balance_frame, self.card_balance = self._make_card("结余")
        cards_row = QHBoxLayout()
        cards_row.addWidget(self.card_expense_frame, 1)
        cards_row.addWidget(self.card_income_frame, 1)
        cards_row.addWidget(self.card_balance_frame, 1)

        # 两个图表：饼图 + 柱状图
        self.pie_fig = Figure(figsize=(4.2, 3.0), tight_layout=True)
        self.pie_canvas = FigureCanvasQTAgg(self.pie_fig)
        self.bar_fig = Figure(figsize=(5.6, 3.0), tight_layout=True)
        self.bar_canvas = FigureCanvasQTAgg(self.bar_fig)
        self.pie_canvas.setMinimumHeight(260)
        self.bar_canvas.setMinimumHeight(260)

        charts_row = QHBoxLayout()
        charts_row.addWidget(self.pie_canvas, 1)
        charts_row.addWidget(self.bar_canvas, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(month_row)
        layout.addLayout(cards_row)
        layout.addLayout(charts_row, 1)

    def _make_card(self, title: str) -> tuple[QFrame, QLabel]:
        """一张统计卡片：灰色圆角底 + 标题 + 大数字。"""
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #f7f7f7; border-radius: 10px; }")
        lay = QVBoxLayout(frame)
        t = QLabel(title)
        t.setStyleSheet("color: #666;")
        v = QLabel("¥0.00")
        v.setStyleSheet("font-size: 20px; font-weight: bold; color: #333;")
        lay.addWidget(t)
        lay.addWidget(v)
        return frame, v

    def _load_months(self) -> None:
        """月份下拉框：有账目的月份（新的在前），当前月兜底排第一。"""
        conn = db.get_connection()
        months = [
            r["month"]
            for r in conn.execute(
                "SELECT DISTINCT substr(date, 1, 7) AS month FROM expenses ORDER BY month DESC"
            )
        ]
        conn.close()
        current = datetime.now().strftime("%Y-%m")
        if current not in months:
            months.insert(0, current)
        self.month_combo.addItems(months)

    # ---------- 刷新 ----------

    def refresh(self) -> None:
        month = self.month_combo.currentText()
        if not month:
            return
        summary = db.get_month_summary(month)
        expense = summary["expense_cents"] / 100
        income = summary["income_cents"] / 100
        balance = income - expense
        self.card_expense.setText(f"¥{expense:,.2f}")
        self.card_expense.setStyleSheet("font-size: 20px; font-weight: bold; color: #c62828;")
        self.card_income.setText(f"¥{income:,.2f}")
        self.card_income.setStyleSheet("font-size: 20px; font-weight: bold; color: #2e7d32;")
        sign = "+" if balance >= 0 else "-"
        self.card_balance.setText(f"{sign}¥{abs(balance):,.2f}")
        self.card_balance.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {'#2e7d32' if balance >= 0 else '#c62828'};"
        )
        self._draw_pie(month)
        self._draw_bar()

    def _draw_pie(self, month: str) -> None:
        """所选月份的支出按一级大类画饼图。"""
        self.pie_fig.clear()
        ax = self.pie_fig.add_subplot(111)
        rows = db.get_month_expense_by_top(month)
        if not rows:
            ax.text(
                0.5, 0.5, "本月暂无支出数据",
                ha="center", va="center", transform=ax.transAxes, fontsize=11,
            )
        else:
            labels = [r["top_name"] for r in rows]
            values = [r["total_cents"] / 100 for r in rows]
            ax.pie(values, labels=labels, autopct="%.1f%%", startangle=90, textprops={"fontsize": 9})
        ax.set_title(f"{month} 支出分类占比", fontsize=11)
        self.pie_canvas.draw()

    def _draw_bar(self) -> None:
        """近12个月收支趋势柱状图（固定以当前月为终点，不受月份选择影响）。"""
        self.bar_fig.clear()
        ax = self.bar_fig.add_subplot(111)
        end_month = datetime.now().strftime("%Y-%m")
        rows = db.get_monthly_trend(12, end_month)
        data = {(r["month"], r["kind"]): r["total_cents"] / 100 for r in rows}
        months = _month_range(end_month, 12)
        expense_vals = [data.get((m, "expense"), 0) for m in months]
        income_vals = [data.get((m, "income"), 0) for m in months]
        x = range(len(months))
        width = 0.38
        ax.bar([i - width / 2 for i in x], expense_vals, width, label="支出", color="#e57373")
        ax.bar([i + width / 2 for i in x], income_vals, width, label="收入", color="#81c784")
        ax.set_xticks(list(x))
        ax.set_xticklabels([m[2:] for m in months], fontsize=8, rotation=45)
        ax.legend(fontsize=9)
        ax.set_ylabel("金额（元）", fontsize=9)
        ax.set_title("近12个月收支趋势", fontsize=11)
        self.bar_canvas.draw()


def _month_range(end_month: str, count: int) -> list[str]:
    """从 end_month 往前数 count 个月的月份列表（升序）。"""
    y, m = map(int, end_month.split("-"))
    end_total = y * 12 + (m - 1)
    start_total = end_total - (count - 1)
    out = []
    for t in range(start_total, end_total + 1):
        yy, mm0 = divmod(t, 12)
        out.append(f"{yy:04d}-{mm0 + 1:02d}")
    return out
