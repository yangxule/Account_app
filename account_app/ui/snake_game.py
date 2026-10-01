"""「小游戏」页面：贪吃蛇（方向键/WASD 控制，吃食物变长，撞墙或撞自己结束）。

基础版功能：移动、吃 🍎 变长、计分、撞墙/撞自己结束、一键重新开始。
和记账功能完全独立：不读写数据库、不碰账本数据。
"""

import random

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# 棋盘 20×20 格，每格 26 像素；蛇每 140 毫秒前进一格
GRID = 20
CELL = 26
TICK_MS = 140

# 配色与清新绿皮肤统一（theme.py）
BOARD_BG = "#eaf3ea"   # 棋盘底色
GRID_LINE = "#d7e5d8"  # 格子线
SNAKE_BODY = "#43a047"  # 蛇身绿
SNAKE_HEAD = "#2e7d32"  # 蛇头深绿
FOOD_RED = "#e53935"   # 食物红


class SnakeBoard(QWidget):
    """游戏棋盘控件：蛇的状态、移动逻辑、键盘控制和画面绘制都在这个类里。"""

    score_changed = Signal(int)  # 每吃一个食物，发出新分数
    game_over = Signal(int)      # 游戏结束时，发出最终分数

    def __init__(self):
        super().__init__()
        self.setFixedSize(GRID * CELL, GRID * CELL)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.timer = QTimer(self)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self.step)
        self.restart()

    # ---------- 游戏状态 ----------

    def restart(self) -> None:
        """开始新一局：蛇回到棋盘中央，分数清零。"""
        mid = GRID // 2
        self.snake = [(mid, mid), (mid - 1, mid), (mid - 2, mid)]  # 头在前
        self.pending = (1, 0)  # 下一步方向；一帧内只允许转向一次，防止原地掉头
        self.score = 0
        self.food = None
        self.over = False
        self._place_food()
        self.score_changed.emit(self.score)
        self.timer.start()
        self.update()

    def _place_food(self) -> bool:
        """把食物随机放到一个空格子上；棋盘被占满时返回 False。"""
        empty = [
            (x, y)
            for x in range(GRID)
            for y in range(GRID)
            if (x, y) not in self.snake
        ]
        if not empty:
            self.food = None
            return False
        self.food = random.choice(empty)
        return True

    def turn(self, dx: int, dy: int) -> None:
        """尝试转向：不允许 180° 原地掉头（会一头撞进自己身体）。"""
        if self.over:
            return
        if (dx, dy) == (-self.pending[0], -self.pending[1]):
            return
        self.pending = (dx, dy)

    def pause(self) -> None:
        self.timer.stop()

    def resume(self) -> None:
        if not self.over:
            self.timer.start()

    def step(self) -> None:
        """蛇前进一格：吃食物变长加分；撞墙或撞自己则游戏结束。"""
        if self.over:
            return
        dx, dy = self.pending
        hx, hy = self.snake[0]
        new_head = (hx + dx, hy + dy)

        # 撞墙
        if not (0 <= new_head[0] < GRID and 0 <= new_head[1] < GRID):
            self._game_over()
            return
        # 撞自己（不吃食物时尾巴会挪走，撞到尾巴那一格不算）
        eating = new_head == self.food
        body = self.snake if eating else self.snake[:-1]
        if new_head in body:
            self._game_over()
            return

        self.snake.insert(0, new_head)
        if eating:
            self.score += 1
            self.score_changed.emit(self.score)
            if not self._place_food():
                self._game_over()  # 棋盘被蛇占满：通关
        else:
            self.snake.pop()
        self.update()

    def _game_over(self) -> None:
        self.over = True
        self.timer.stop()
        self.game_over.emit(self.score)
        self.update()

    # ---------- 键盘控制 ----------

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self.turn(0, -1)
        elif key in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self.turn(0, 1)
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self.turn(-1, 0)
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self.turn(1, 0)
        else:
            super().keyPressEvent(event)

    # ---------- 绘制 ----------

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # 棋盘底 + 格子线
        p.fillRect(self.rect(), QColor(BOARD_BG))
        p.setPen(QColor(GRID_LINE))
        for i in range(GRID + 1):
            p.drawLine(i * CELL, 0, i * CELL, GRID * CELL)
            p.drawLine(0, i * CELL, GRID * CELL, i * CELL)
        # 食物：红苹果
        if self.food is not None:
            fx, fy = self.food
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(FOOD_RED))
            p.drawEllipse(QRectF(fx * CELL + 4, fy * CELL + 4, CELL - 8, CELL - 8))
        # 蛇：头深绿、身子绿色，圆角方块
        for i, (x, y) in enumerate(self.snake):
            p.setBrush(QColor(SNAKE_HEAD if i == 0 else SNAKE_BODY))
            p.drawRoundedRect(QRectF(x * CELL + 2, y * CELL + 2, CELL - 4, CELL - 4), 6, 6)
        # 结束遮罩
        if self.over:
            p.fillRect(self.rect(), QColor(0, 0, 0, 60))
            font = p.font()
            font.setPointSize(20)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor("#c62828"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "游戏结束")


class SnakePage(QWidget):
    """「小游戏」标签页：标题 + 分数 + 棋盘 + 操作提示 + 重新开始按钮。"""

    HINT = "💡 用键盘方向键 ↑ ↓ ← → 控制蛇移动，撞墙或撞到自己则游戏结束"

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        # 顶行：标题 …… 分数
        title = QLabel("🐍 贪吃蛇")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2e7d32;")
        self.score_label = QLabel("分数：0")
        self.score_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2e7d32;")
        top_row = QHBoxLayout()
        top_row.addWidget(title)
        top_row.addStretch()
        top_row.addWidget(self.score_label)

        # 棋盘：包在白色圆角卡片里（外观由 theme.py 的 statCard 统一定义）
        self.board = SnakeBoard()
        self.board.score_changed.connect(
            lambda s: self.score_label.setText(f"分数：{s}")
        )
        self.board.game_over.connect(self._on_game_over)
        card = QFrame()
        card.setObjectName("statCard")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(12, 12, 12, 12)
        card_lay.addWidget(self.board, 0, Qt.AlignmentFlag.AlignHCenter)

        # 底部：提示语 + 重新开始按钮
        self.hint_label = QLabel(self.HINT)
        self.hint_label.setStyleSheet("color: #666;")
        self.restart_btn = QPushButton("↺ 重新开始")
        self.restart_btn.clicked.connect(self._restart)
        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.hint_label)
        bottom_row.addStretch()
        bottom_row.addWidget(self.restart_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addLayout(bottom_row)
        layout.addStretch()

    # ---------- 状态联动 ----------

    def _on_game_over(self, score: int) -> None:
        self.hint_label.setStyleSheet("color: #c62828; font-weight: bold;")
        self.hint_label.setText(
            f"💥 游戏结束！最终分数 {score}，点「重新开始」再来一局"
        )

    def _restart(self) -> None:
        self.hint_label.setStyleSheet("color: #666;")
        self.hint_label.setText(self.HINT)
        self.board.restart()
        self.board.setFocus()
