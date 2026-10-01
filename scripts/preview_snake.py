"""开发辅助：抓一张「小游戏」贪吃蛇页面的截图到 /tmp/account_preview/。

注意：会在屏幕上闪现一次 App 窗口（需要真实显示器，offscreen 抓不到按钮效果）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from account_app import db
from account_app.ui import theme
from account_app.ui.main_window import MainWindow

app = QApplication([])
theme.apply(app)

# 草稿纸数据库，不碰真实账本 data/account.db
db.DB_PATH = Path("/tmp/account_snake_preview.db")
if db.DB_PATH.exists():
    db.DB_PATH.unlink()
db.init_db()

win = MainWindow()
win.show()
tabs = win.centralWidget()
tabs.setCurrentIndex(5)  # 切到「小游戏」标签

out_dir = Path("/tmp/account_preview")
out_dir.mkdir(exist_ok=True)


def capture() -> None:
    # 让蛇先走几步，画面更生动；顺便让蛇吃一个食物再截一张
    win.snake_page.board.setFocus()
    win.grab().save(str(out_dir / "snake_1_游戏页.jpg"), "JPEG", 90)
    app.quit()


QTimer.singleShot(800, capture)
app.exec()
print("已保存到", out_dir / "snake_1_游戏页.jpg")
