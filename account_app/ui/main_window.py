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
        self.resize(1000, 680)

        self.expense_form = ExpenseForm()
        self.expense_list = ExpenseList()
        self.stats_page = StatsPage()

        tabs = QTabWidget()
        tabs.addTab(self.expense_form, "记一笔")
        tabs.addTab(self.expense_list, "明细")
        tabs.addTab(self.stats_page, "统计")
        tabs.addTab(CategoryPage(), "分类设置")
        tabs.addTab(BudgetPage(), "预算")
        self.setCentralWidget(tabs)

        # 记一笔保存后，明细页和统计页自动刷新
        self.expense_form.saved.connect(self.expense_list.refresh)
        self.expense_form.saved.connect(self.stats_page.refresh)
        # 切到某个页面时也刷新一次，保证数据最新
        tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int) -> None:
        tab = self.centralWidget().widget(index)
        if tab is self.expense_list:
            self.expense_list.refresh()
        elif tab is self.stats_page:
            self.stats_page.refresh()
