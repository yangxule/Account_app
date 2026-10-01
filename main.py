"""Account 记账App 入口。启动方式：python main.py（或直接运行 start.sh）。"""

import sys

from PySide6.QtWidgets import QApplication

from account_app import db
from account_app.ui import theme
from account_app.ui.main_window import MainWindow


def main() -> None:
    db.init_db()  # 首次运行自动建数据库、写入默认分类
    app = QApplication(sys.argv)
    theme.apply(app)  # 套上清新绿皮肤
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
