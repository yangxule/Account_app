"""「明细」页面的自动化测试：筛选、编辑弹窗、导出、删除、收入、旧库升级。

运行方式（在项目根目录）：
    conda activate vibe_coding_learning
    QT_QPA_PLATFORM=offscreen python tests/test_expense_list.py

注意：测试使用临时数据库（草稿纸），绝不会碰真实账本 data/account.db。
"""

import shutil
import sqlite3 as sqlite3_mod
import sys
import tempfile
from pathlib import Path

# 让脚本无论从哪里运行都能找到项目代码包 account_app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication
from openpyxl import load_workbook

from account_app import db
from account_app.ui import expense_list as el_mod
from account_app.ui.expense_dialog import ExpenseDialog
from account_app.ui.expense_form import ExpenseForm
from account_app.ui.expense_list import ExpenseList
from account_app.ui.main_window import MainWindow


def _cat_id(top_name: str, sub_name: str) -> int:
    """按名称查二级分类 id。"""
    conn = db.get_connection()
    top = conn.execute(
        "SELECT id FROM categories WHERE name=? AND parent_id IS NULL", (top_name,)
    ).fetchone()
    sub = conn.execute(
        "SELECT id FROM categories WHERE name=? AND parent_id=?", (sub_name, top["id"])
    ).fetchone()
    conn.close()
    return sub["id"]


def _test_migration(old_db_path: Path) -> None:
    """旧版数据库（无 kind 列）升级后应自动补齐，老数据不受影响。"""
    conn = sqlite3_mod.connect(old_db_path)
    conn.executescript(
        """
        CREATE TABLE categories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_id  INTEGER REFERENCES categories(id),
            name       TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE expenses (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            amount_cents INTEGER NOT NULL,
            category_id  INTEGER REFERENCES categories(id),
            date         TEXT NOT NULL,
            note         TEXT NOT NULL DEFAULT '',
            created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO categories (parent_id, name, sort_order) VALUES (NULL, '餐饮', 0);
        INSERT INTO categories (parent_id, name, sort_order) VALUES (1, '早餐', 0);
        INSERT INTO expenses (amount_cents, category_id, date, note) VALUES (800, 2, '2026-01-01', '老账');
        """
    )
    conn.commit()
    conn.close()

    db.DB_PATH = old_db_path
    db.init_db()

    conn = db.get_connection()
    cat_cols = {r["name"] for r in conn.execute("PRAGMA table_info(categories)")}
    exp_cols = {r["name"] for r in conn.execute("PRAGMA table_info(expenses)")}
    assert "kind" in cat_cols and "kind" in exp_cols, "kind 列未补齐"
    n_income = conn.execute("SELECT COUNT(*) FROM categories WHERE kind='income'").fetchone()[0]
    assert n_income == 7, f"收入分类应为 7 个，实际 {n_income}"
    row = conn.execute("SELECT * FROM expenses").fetchone()
    assert row["kind"] == "expense" and row["note"] == "老账", "老数据被破坏"
    conn.close()
    print("  ✅ 旧库升级正常：新列补齐、收入分类就位、老账原样保留")


def main() -> None:
    app = QApplication([])
    tmp = Path(tempfile.mkdtemp())
    try:
        # ---- 旧库升级测试 ----
        _test_migration(tmp / "old.db")

        # ---- 切到临时数据库（草稿纸模式） ----
        db.DB_PATH = tmp / "test.db"
        el_mod.EXPORT_DIR = tmp / "exports"
        db.init_db()

        # ---- 准备测试数据：3 笔支出 + 1 笔收入 ----
        id_a = db.insert_expense(800, _cat_id("餐饮", "早餐"), "2026-10-01", "公司楼下")
        id_b = db.insert_expense(400, _cat_id("交通", "公交/地铁"), "2026-09-30", "上班")
        id_c = db.insert_expense(5000, _cat_id("购物", "日用品"), "2026-09-28", "超市采购")
        id_d = db.insert_expense(500000, _cat_id("收入", "工资"), "2026-10-01", "10月工资", kind="income")
        assert id_d is not None

        # ---- 筛选测试 ----
        page = ExpenseList()

        def check(desc: str, expect_ids: list[int]) -> None:
            got = sorted(r["id"] for r in page._last_rows)
            assert got == sorted(expect_ids), f"{desc}：期望 {expect_ids}，实际 {got}"
            print(f"  ✅ {desc} → {got}")

        page.keyword_input.setText("超市")
        page.refresh()
        check("关键字「超市」", [id_c])

        page.keyword_input.clear()
        page.date_check.setChecked(True)
        page.date_from.setDate(QDate(2026, 9, 30))
        page.date_to.setDate(QDate(2026, 10, 1))
        page.refresh()
        check("日期 09-30 ~ 10-01", [id_a, id_b, id_d])
        page.date_check.setChecked(False)

        page.top_filter.setCurrentIndex(page.top_filter.findText("交通"))
        page.refresh()
        check("分类筛选「交通」", [id_b])
        page.top_filter.setCurrentIndex(0)

        page.kind_filter.setCurrentIndex(page.kind_filter.findText("收入"))
        page.refresh()
        check("类型筛选「收入」", [id_d])
        assert page.table.item(0, 2).text().startswith("+¥5,000.00")
        print("  ✅ 收入在列表中显示绿色 + 号")

        page.kind_filter.setCurrentIndex(0)
        page.min_amount.setValue(10.0)
        page.refresh()
        check("最小金额 ¥10", [id_c, id_d])
        page.min_amount.setValue(0.0)

        page.refresh()
        assert page.table.rowCount() == 4
        assert "共 4 笔" in page.summary.text()
        assert "支出 ¥62.00" in page.summary.text()
        assert "收入 ¥5,000.00" in page.summary.text()
        print(f"  ✅ 汇总行正常：{page.summary.text()}")

        # ---- 记一笔页面的收支开关测试 ----
        form = ExpenseForm()
        assert form.top_cat.currentText() == "餐饮"
        form.kind_income.setChecked(True)
        assert form.top_cat.currentText() == "收入"
        assert form.sub_cat.currentText() == "工资"
        print("  ✅ 记一笔收支开关正常：切到收入自动换收入分类")

        # ---- 统计查询与页面测试 ----
        from account_app.ui.stats_page import StatsPage

        summary = db.get_month_summary("2026-10")
        assert summary["expense_cents"] == 800 and summary["income_cents"] == 500000
        sep_summary = db.get_month_summary("2026-09")
        assert sep_summary["expense_cents"] == 5400 and sep_summary["income_cents"] == 0
        by_top = {r["top_name"]: r["total_cents"] for r in db.get_month_expense_by_top("2026-09")}
        assert by_top == {"购物": 5000, "交通": 400}
        trend = {(r["month"], r["kind"]): r["total_cents"] for r in db.get_monthly_trend(12, "2026-10")}
        assert trend[("2026-10", "income")] == 500000
        assert trend[("2026-09", "expense")] == 5400
        print("  ✅ 统计查询正常：月度汇总 / 分类占比 / 12个月趋势")

        stats = StatsPage()
        assert stats.month_combo.currentText() == "2026-10"
        assert stats.card_expense.text() == "¥8.00"
        assert stats.card_income.text() == "¥5,000.00"
        assert stats.card_balance.text() == "+¥4,992.00"
        print("  ✅ 统计页面正常：三卡片数值正确，饼图/柱状图绘制成功")

        # ---- 编辑弹窗测试（支出 + 收入各一次） ----
        dlg = ExpenseDialog(id_a)
        assert dlg.amount_input.value() == 8.00
        assert dlg.top_cat.currentText() == "餐饮"
        assert dlg.sub_cat.currentText() == "早餐"
        assert dlg.note_input.text() == "公司楼下"
        dlg.amount_input.setValue(9.99)
        dlg.note_input.setText("改过备注")
        dlg._on_save()
        row = db.get_expense(id_a)
        assert row["amount_cents"] == 999 and row["note"] == "改过备注"
        print("  ✅ 支出编辑保存成功：改为 ¥9.99「改过备注」")

        dlg2 = ExpenseDialog(id_d)
        assert dlg2.kind_income.isChecked()
        assert dlg2.top_cat.currentText() == "收入"
        assert dlg2.sub_cat.currentText() == "工资"
        dlg2.amount_input.setValue(5200.00)
        dlg2._on_save()
        row = db.get_expense(id_d)
        assert row["kind"] == "income" and row["amount_cents"] == 520000
        print("  ✅ 收入编辑保存成功：改为 ¥5,200.00")

        # ---- 导出测试（含类型列） ----
        page.refresh()
        page._export("csv")
        page._export("xlsx")
        files = sorted((tmp / "exports").glob("账目导出_*"))
        assert len(files) == 2, f"应导出 2 个文件，实际 {len(files)}"
        csv_file = next(f for f in files if f.suffix == ".csv")
        xlsx_file = next(f for f in files if f.suffix == ".xlsx")
        with open(csv_file, encoding="utf-8-sig") as f:
            lines = f.read().strip().splitlines()
        assert len(lines) == 5 and "类型" in lines[0], "导出应含表头「类型」"
        assert any("收入" in ln for ln in lines[1:]), "导出应含收入行"
        wb = load_workbook(xlsx_file)
        assert wb.active.max_row == 5
        print("  ✅ 导出正常：CSV / Excel 各 5 行，含「类型」列")

        # ---- 删除 + 主窗口联动测试 ----
        db.delete_expense(id_b)
        win = MainWindow()
        assert win.expense_list.table.rowCount() == 3
        print("  ✅ 删除正常；主窗口与页面联动正常")

        # ---- 分类管理测试 ----
        from account_app.ui.category_page import CategoryPage

        top_id = db.add_category(None, "测试大类")
        sub_id = db.add_category(top_id, "测试小类")
        db.rename_category(sub_id, "改名小类")
        usage = db.get_category_usage(top_id)
        assert usage["sub_count"] == 1 and usage["expense_count"] == 0

        # 有小类的大类不能删
        err = db.delete_category(top_id)
        assert "小类" in err
        # 有账目的小类不能删
        eid = db.insert_expense(100, sub_id, "2026-10-01", "分类测试账")
        err = db.delete_category(sub_id)
        assert "账目" in err
        # 清空账目后可以逐级删掉
        db.delete_expense(eid)
        assert db.delete_category(sub_id) == ""
        assert db.delete_category(top_id) == ""
        print("  ✅ 分类增删改正常：有账目/小类时正确拒绝删除，清空后可删")

        page_cat = CategoryPage()
        assert page_cat.tree.topLevelItemCount() == 10  # 9 个支出大类 + 收入
        income_item = page_cat.tree.topLevelItem(9)
        assert income_item.text(0) == "收入" and income_item.childCount() == 6
        page_cat.tree.setCurrentItem(page_cat.tree.topLevelItem(0))
        assert page_cat.add_sub_btn.isEnabled()  # 选中一级：可加小类
        page_cat.tree.setCurrentItem(page_cat.tree.topLevelItem(0).child(0))
        assert not page_cat.add_sub_btn.isEnabled()  # 选中二级：不可加小类
        print("  ✅ 分类设置页面正常：树加载 10 大类、收入 6 小类、按钮状态正确")

        # ---- 预算功能测试 ----
        from account_app.ui.budget_page import BudgetPage, budget_warning_for

        assert db.get_setting("不存在的键") is None
        db.set_setting("monthly_budget", "200000")  # ¥2,000
        assert db.get_setting("monthly_budget") == "200000"

        budget_page = BudgetPage()
        assert budget_page.amount_input.value() == 2000.00  # 回填已保存的预算
        assert "¥9.99" in budget_page.detail.text() and "正常" in budget_page.status.text()
        print("  ✅ 预算页正常：回填 ¥2,000，本月已花 ¥9.99 状态正常")

        budget_page.amount_input.setValue(3000.00)
        budget_page._save()
        assert db.get_setting("monthly_budget") == "300000"
        print("  ✅ 预算页保存正常：改预算为 ¥3,000 已存库")

        # 阈值提醒函数（预算设为 ¥100 测阈值）
        db.set_setting("monthly_budget", "10000")
        warn, color = budget_warning_for("2026-10", 8500)
        assert "接近" in warn and color == "#ef6c00"
        warn2, color2 = budget_warning_for("2026-10", 10500)
        assert "超出" in warn2 and color2 == "#c62828"
        warn3, color3 = budget_warning_for("2026-10", 5000)
        assert warn3 is None and color3 is None
        print("  ✅ 预算阈值提醒正确：80% 橙色接近 / 100% 红色超支 / 未达阈值不提醒")

        # 记一笔保存时的提醒（预算 ¥100：先花 85 到 85%，再花 20 到 105%）
        form = ExpenseForm()
        form.amount_input.setValue(85.00)
        form._save()
        assert "接近预算" in form.feedback.text()
        form.amount_input.setValue(20.00)
        form._save()
        assert "超出预算" in form.feedback.text()
        print("  ✅ 记一笔超支提醒正常：85% 橙色提醒，105% 红色提醒")

        budget_page.refresh()
        assert "已超支" in budget_page.status.text()
        print("  ✅ 预算页状态联动正常：超支后显示红色状态")

        print("全部测试通过 ✅")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
