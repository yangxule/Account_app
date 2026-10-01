"""「小游戏」贪吃蛇的自动化测试：移动、吃食、计分、撞墙/撞己、重开、暂停、标签页集成。

运行方式（在项目根目录）：
    conda activate vibe_coding_learning
    QT_QPA_PLATFORM=offscreen python tests/test_snake_game.py

注意：贪吃蛇本身不读写数据库；主窗口测试使用临时数据库（草稿纸），
绝不写真实账本 data/account.db。
"""

import shutil
import sys
import tempfile
from pathlib import Path

# 让脚本无论从哪里运行都能找到项目代码包 account_app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from account_app import db
from account_app.ui import theme
from account_app.ui.main_window import MainWindow
from account_app.ui.snake_game import GRID, SnakeBoard, SnakePage


def main() -> None:
    app = QApplication([])
    theme.apply(app)  # V1.1 皮肤：验证游戏页控件也能正常套用
    tmp = Path(tempfile.mkdtemp())
    try:
        # ---- 棋盘逻辑测试（不依赖数据库） ----
        board = SnakeBoard()
        assert not board.over and len(board.snake) == 3 and board.score == 0
        assert board.timer.isActive()
        print("  ✅ 初始状态正常：蛇长 3、分数 0、计时器已启动")

        # 转向：允许转向，但禁止 180° 原地掉头
        board.turn(0, 1)  # 向右走时按「下」（dy=+1）→ 转向下
        assert board.pending == (0, 1)
        board.turn(0, -1)  # 向下走时按「上」= 180° 掉头，应被忽略
        assert board.pending == (0, 1), "180° 原地掉头应该被忽略"
        print("  ✅ 转向正常：允许转向，禁止 180° 掉头")

        # 移动：明确方向向右，走一步蛇头前移、长度不变
        board.pending = (1, 0)
        old_head = board.snake[0]
        board.step()
        assert board.snake[0] == (old_head[0] + 1, old_head[1])
        assert len(board.snake) == 3
        print("  ✅ 移动正常：蛇头前进一格，长度不变")

        # 吃食物：食物在蛇头正前方，走一步应加分变长，新食物长在空格上
        hx, hy = board.snake[0]
        board.food = (hx + 1, hy)
        board.step()
        assert board.score == 1 and len(board.snake) == 4
        assert board.food not in board.snake, "新食物不应长在蛇身上"
        print("  ✅ 吃食正常：+1 分、变长一节、新食物在空格上")

        # 撞自己：蛇头下一步撞进身体（非尾巴），应结束游戏
        board.timer.stop()
        board.snake = [(5, 5), (5, 6), (6, 6), (6, 5), (6, 4), (5, 4), (4, 4)]
        board.pending = (0, -1)  # 从 (5,5) 向上撞向 (5,4)（自己身体）
        board.food = (0, 0)
        board.over = False
        board.step()
        assert board.over, "撞到自己身体应该结束游戏"
        print("  ✅ 撞自己正常：游戏结束")

        # 撞到尾巴不算（不吃食物时尾巴会挪走）：绕圈蛇头追尾应能安全通过
        board.snake = [(4, 5), (4, 4), (5, 4), (6, 4), (6, 5), (6, 6), (5, 6), (5, 5)]
        board.pending = (1, 0)  # 从 (4,5) 向右撞向 (5,5)（尾巴）
        board.food = (0, 0)
        board.over = False
        board.step()
        assert not board.over, "撞到尾巴（它会挪走）不应结束游戏"
        print("  ✅ 撞尾巴豁免正常：追尾安全通过")

        # 撞墙：贴着右边墙向右走，应结束游戏
        board.snake = [(GRID - 1, 5)]
        board.pending = (1, 0)
        board.food = (0, 0)
        board.over = False
        board.step()
        assert board.over, "撞墙应该结束游戏"
        print("  ✅ 撞墙正常：游戏结束")

        # 暂停 / 恢复：暂停停表；没结束时恢复走表；结束时不复活
        board.pause()
        assert not board.timer.isActive()
        board.over = False
        board.resume()
        assert board.timer.isActive()
        board._game_over()
        board.resume()
        assert not board.timer.isActive(), "游戏结束后恢复不应重新走表"
        print("  ✅ 暂停/恢复正常：结束状态不会复活")

        # 重开：一切复位
        board.restart()
        assert not board.over and len(board.snake) == 3 and board.score == 0
        assert board.timer.isActive()
        board.timer.stop()
        print("  ✅ 重新开始正常：蛇、分数、计时器全部复位")

        # ---- 页面与主窗口集成测试（临时数据库） ----
        db.DB_PATH = tmp / "test.db"
        db.init_db()

        page = SnakePage()
        assert page.score_label.text() == "分数：0"
        # 模拟吃一个食物：页面分数标签应联动
        hx, hy = page.board.snake[0]
        page.board.food = (hx + 1, hy)
        page.board.step()
        assert page.score_label.text() == "分数：1", page.score_label.text()
        # 游戏结束：提示语变红并显示最终分数
        page.board.snake = [(GRID - 1, 5)]
        page.board.pending = (1, 0)
        page.board.food = (0, 0)
        page.board.over = False
        page.board.step()
        assert page.board.over and "游戏结束" in page.hint_label.text()
        assert "分数 1" in page.hint_label.text(), page.hint_label.text()
        # 重新开始：提示语复原、分数归零
        page._restart()
        assert page.score_label.text() == "分数：0" and "方向键" in page.hint_label.text()
        page.board.timer.stop()
        print("  ✅ 页面联动正常：分数实时更新、结束提示、重新开始复位")

        win = MainWindow()
        tabs = win.centralWidget()
        assert tabs.count() == 6, f"应有 6 个标签页，实际 {tabs.count()}"
        assert tabs.tabText(5) == "🎮 小游戏"
        assert tabs.widget(5) is win.snake_page
        # 棋盘要能抢到键盘焦点，方向键才能控制蛇
        assert win.snake_page.board.focusPolicy() == Qt.FocusPolicy.StrongFocus
        # 切到小游戏页：恢复走表；切走：暂停
        tabs.setCurrentIndex(5)
        win._on_tab_changed(5)
        assert win.snake_page.board.timer.isActive()
        tabs.setCurrentIndex(0)
        win._on_tab_changed(0)
        assert not win.snake_page.board.timer.isActive()
        print("  ✅ 主窗口集成正常：第 6 个标签「🎮 小游戏」，切走暂停、切回继续")

        print("全部测试通过 ✅")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
