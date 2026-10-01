"""数据库：建表、初始化默认分类、提供连接。"""

import sqlite3

from account_app.config import DB_PATH

# 内置默认分类树：一级大类 -> 其下的二级小类
DEFAULT_CATEGORIES = [
    ("餐饮", ["早餐", "午餐/晚餐", "外卖", "零食/饮料", "买菜/食材", "聚餐"]),
    ("交通", ["公交/地铁", "打车/网约车", "加油/充电", "停车费", "火车/飞机"]),
    ("居住", ["房租/房贷", "水/电/燃气", "物业费", "宽带/话费", "家居日用", "维修"]),
    ("购物", ["衣服/鞋包", "日用品", "数码/家电", "美妆/个护"]),
    ("娱乐", ["电影/演出", "游戏", "旅游", "运动/健身", "会员订阅"]),
    ("医疗健康", ["看病/买药", "体检", "保健品"]),
    ("教育学习", ["买书/文具", "课程/培训", "考试/报名"]),
    ("人情往来", ["红包/礼金", "请客送礼", "孝敬长辈"]),
    ("其他", ["其他支出"]),
]


def get_connection() -> sqlite3.Connection:
    """打开数据库连接。用完记得 conn.close()。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """建表 + 首次运行时写入默认分类。可重复调用，不会破坏已有数据。"""
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id  INTEGER REFERENCES categories(id),  -- NULL=一级大类，否则=所属大类id
                name       TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0          -- 显示顺序
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_cents INTEGER NOT NULL,  -- 金额，单位：分（12.34元存为1234，避免小数误差）
                category_id  INTEGER REFERENCES categories(id),  -- 二级小类
                date         TEXT NOT NULL,      -- 花销日期，格式 YYYY-MM-DD
                note         TEXT NOT NULL DEFAULT '',  -- 备注（可空）
                created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))  -- 记录时间
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,  -- 如 monthly_budget（月度预算，单位：分）
                value TEXT
            );
            """
        )
        if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
            _seed_categories(conn)
        conn.commit()
    finally:
        conn.close()


def _seed_categories(conn: sqlite3.Connection) -> None:
    """写入内置分类树。"""
    for i, (top_name, subs) in enumerate(DEFAULT_CATEGORIES):
        cur = conn.execute(
            "INSERT INTO categories (parent_id, name, sort_order) VALUES (NULL, ?, ?)",
            (top_name, i),
        )
        top_id = cur.lastrowid
        for j, sub_name in enumerate(subs):
            conn.execute(
                "INSERT INTO categories (parent_id, name, sort_order) VALUES (?, ?, ?)",
                (top_id, sub_name, j),
            )


# ---------- 分类查询 ----------


def get_top_categories() -> list[sqlite3.Row]:
    """所有一级大类（按显示顺序）。"""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT id, name FROM categories WHERE parent_id IS NULL ORDER BY sort_order"
        ).fetchall()
    finally:
        conn.close()


def get_sub_categories(top_id: int) -> list[sqlite3.Row]:
    """某个一级大类下的所有二级小类（按显示顺序）。"""
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT id, name FROM categories WHERE parent_id = ? ORDER BY sort_order",
            (top_id,),
        ).fetchall()
    finally:
        conn.close()


# ---------- 账目读写 ----------


def insert_expense(amount_cents: int, category_id: int, date: str, note: str = "") -> None:
    """新增一笔账。amount_cents：金额（单位：分）；date：格式 YYYY-MM-DD。"""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO expenses (amount_cents, category_id, date, note) VALUES (?, ?, ?, ?)",
            (amount_cents, category_id, date, note),
        )
        conn.commit()
    finally:
        conn.close()


def get_expenses_by_date(date: str) -> list[sqlite3.Row]:
    """某一天的全部账目（含分类名），按记录时间倒序。"""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT e.id, e.amount_cents, e.note,
                   s.name AS sub_name, t.name AS top_name
            FROM expenses e
            JOIN categories s ON s.id = e.category_id
            LEFT JOIN categories t ON t.id = s.parent_id
            WHERE e.date = ?
            ORDER BY e.created_at DESC, e.id DESC
            """,
            (date,),
        ).fetchall()
    finally:
        conn.close()
