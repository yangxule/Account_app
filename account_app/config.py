"""全局配置：常量集中放在这里，方便统一修改。"""

from pathlib import Path

APP_NAME = "Account 记账"
APP_VERSION = "1.1.0"

# 项目根目录（main.py 所在文件夹）
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据库文件位置：项目根目录下的 data/account.db
DB_PATH = BASE_DIR / "data" / "account.db"
