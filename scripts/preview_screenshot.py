"""生成界面预览截图（仅用于本地查看皮肤效果，不碰真实账本）。

运行方式（在项目根目录）：
    conda activate vibe_coding_learning
    QT_QPA_PLATFORM=offscreen python scripts/preview_screenshot.py

截图输出到 /tmp/account_preview/，可用图片查看器打开。
注意：使用临时数据库（草稿纸）+ 示例数据，绝不写入真实账本 data/account.db。
"""

import shutil
import sys
import tempfile
from pathlib import Path

# 让脚本无论从哪里运行都能找到项目代码包 account_app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from account_app import db
from account_app.ui import theme
from account_app.ui.main_window import MainWindow

OUT_DIR = Path("/tmp/account_preview")


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


def main() -> None:
    tmp = Path(tempfile.mkdtemp())
    try:
        # ---- 草稿纸数据库 + 示例数据 ----
        db.DB_PATH = tmp / "preview.db"
        db.init_db()
        db.insert_expense(800, _cat_id("餐饮", "早餐"), "2026-10-01", "公司楼下")
        db.insert_expense(3500, _cat_id("餐饮", "外卖"), "2026-10-01", "午饭点外卖")
        db.insert_expense(5200, _cat_id("居住", "宽带/话费"), "2026-10-01", "10月话费")
        db.insert_expense(12000, _cat_id("交通", "公交/地铁"), "2026-09-28", "地铁月票")
        db.insert_expense(26800, _cat_id("购物", "日用品"), "2026-09-20", "超市采购")
        db.insert_expense(12900, _cat_id("娱乐", "电影/演出"), "2026-09-15", "周末电影")
        db.insert_expense(500000, _cat_id("收入", "工资"), "2026-09-30", "9月工资", kind="income")
        db.insert_expense(20000, _cat_id("收入", "红包/礼金"), "2026-10-01", "国庆红包", kind="income")
        db.set_setting("monthly_budget", "300000")  # 预算 ¥3,000

        # ---- 建窗口、套皮肤、逐页截图 ----
        app = QApplication([])
        theme.apply(app)
        win = MainWindow()
        win.resize(1000, 680)
        win.show()

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        tabs = win.centralWidget()
        names = ["记一笔", "明细", "统计", "分类设置", "预算"]

        def capture_all() -> None:
            for i, name in enumerate(names):
                tabs.setCurrentIndex(i)  # 切页会触发对应页面的刷新
                app.processEvents()
                app.processEvents()
                path = OUT_DIR / f"v1.1_{i + 1}_{name}.jpg"  # JPEG 通用性最好，随处可看
                win.grab().save(str(path))
                print(f"已生成：{path}")
            print("全部截图完成 ✅")
            app.quit()

        QTimer.singleShot(500, capture_all)  # 等窗口完整渲染后再逐页截图
        app.exec()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
