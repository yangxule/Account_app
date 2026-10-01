"""主窗口：用左侧标签页切换各功能页面。"""

from PySide6.QtWidgets import QMainWindow, QTabWidget

from account_app.config import APP_NAME
from account_app.ui.budget_page import BudgetPage
from account_app.ui.category_page import CategoryPage
from account_app.ui.expense_form import ExpenseForm
from account_app.ui.expense_list import ExpenseList
from account_app.ui.stats_page import StatsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 640)

        tabs = QTabWidget()
        tabs.addTab(ExpenseForm(), "记一笔")
        tabs.addTab(ExpenseList(), "明细")
        tabs.addTab(StatsPage(), "统计")
        tabs.addTab(CategoryPage(), "分类设置")
        tabs.addTab(BudgetPage(), "预算")
        self.setCentralWidget(tabs)
