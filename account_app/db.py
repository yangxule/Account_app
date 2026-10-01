"""数据库：建表、初始化默认分类、旧库升级、提供连接。"""

import sqlite3
from datetime import datetime

from account_app.config import DB_PATH

# 内置支出分类树：一级大类 -> 其下的二级小类
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

# 内置收入分类树（kind='income'）
INCOME_CATEGORIES = [
    ("收入", ["工资", "红包/礼金", "理财收益", "兼职外快", "报销返款", "其他收入"]),
]


def get_connection() -> sqlite3.Connection:
    """打开数据库连接。用完记得 conn.close()。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """建表 + 旧库升级 + 首次运行时写入默认分类。可重复调用，不会破坏已有数据。"""
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id  INTEGER REFERENCES categories(id),  -- NULL=一级大类，否则=所属大类id
                name       TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,         -- 显示顺序
                kind       TEXT NOT NULL DEFAULT 'expense'     -- 'expense'=支出分类，'income'=收入分类
            );

            CREATE TABLE IF NOT EXISTS expenses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_cents INTEGER NOT NULL,  -- 金额，单位：分（12.34元存为1234，避免小数误差）
                category_id  INTEGER REFERENCES categories(id),  -- 二级小类
                date         TEXT NOT NULL,      -- 收支日期，格式 YYYY-MM-DD
                note         TEXT NOT NULL DEFAULT '',  -- 备注（可空）
                kind         TEXT NOT NULL DEFAULT 'expense',  -- 'expense'=支出，'income'=收入
                created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))  -- 记录时间
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,  -- 如 monthly_budget（月度预算，单位：分）
                value TEXT
            );
            """
        )
        _migrate(conn)
        # 首次运行：写入支出分类
        if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
            _seed_categories(conn, DEFAULT_CATEGORIES, "expense", start_order=0)
        # 老库升级 / 首次运行：写入收入分类
        if conn.execute("SELECT COUNT(*) FROM categories WHERE kind='income'").fetchone()[0] == 0:
            _seed_categories(conn, INCOME_CATEGORIES, "income", start_order=len(DEFAULT_CATEGORIES))
        conn.commit()
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """旧版数据库升级：补上后来新增的列。"""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(categories)")}
    if "kind" not in cols:
        conn.execute("ALTER TABLE categories ADD COLUMN kind TEXT NOT NULL DEFAULT 'expense'")
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(expenses)")}
    if "kind" not in cols:
        conn.execute("ALTER TABLE expenses ADD COLUMN kind TEXT NOT NULL DEFAULT 'expense'")


def _seed_categories(
    conn: sqlite3.Connection, categories: list, kind: str, start_order: int = 0
) -> None:
    """把一套分类树写入数据库。"""
    for i, (top_name, subs) in enumerate(categories):
        cur = conn.execute(
            "INSERT INTO categories (parent_id, name, sort_order, kind) VALUES (NULL, ?, ?, ?)",
            (top_name, start_order + i, kind),
        )
        top_id = cur.lastrowid
        for j, sub_name in enumerate(subs):
            conn.execute(
                "INSERT INTO categories (parent_id, name, sort_order, kind) VALUES (?, ?, ?, ?)",
                (top_id, sub_name, j, kind),
            )


# ---------- 分类查询 ----------


def get_top_categories(kind: str | None = None) -> list[sqlite3.Row]:
    """所有一级大类（按显示顺序）。kind 传 'expense' 或 'income' 只取一类，None 取全部。"""
    sql = "SELECT id, name, kind FROM categories WHERE parent_id IS NULL"
    params: list = []
    if kind is not None:
        sql += " AND kind = ?"
        params.append(kind)
    sql += " ORDER BY sort_order"
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def add_category(parent_id: int | None, name: str, kind: str = "expense") -> int:
    """新增分类（parent_id=None 是一级大类，否则是它下面的小类），返回新分类 id。"""
    conn = get_connection()
    try:
        # sort_order 排在同级最后
        if parent_id is None:
            n = conn.execute(
                "SELECT COUNT(*) FROM categories WHERE parent_id IS NULL AND kind = ?",
                (kind,),
            ).fetchone()[0]
        else:
            n = conn.execute(
                "SELECT COUNT(*) FROM categories WHERE parent_id = ?", (parent_id,)
            ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO categories (parent_id, name, sort_order, kind) VALUES (?, ?, ?, ?)",
            (parent_id, name, n, kind),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def rename_category(category_id: int, name: str) -> None:
    """给分类改名。"""
    conn = get_connection()
    try:
        conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
        conn.commit()
    finally:
        conn.close()


def get_category_usage(category_id: int) -> sqlite3.Row:
    """分类的使用情况：小类数量 + 直接挂在上面的账目数量（判断能否删除）。"""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM categories WHERE parent_id = ?) AS sub_count,
                (SELECT COUNT(*) FROM expenses WHERE category_id = ?) AS expense_count
            """,
            (category_id, category_id),
        ).fetchone()
    finally:
        conn.close()


def delete_category(category_id: int) -> str:
    """删除分类。下面还有小类或账目时拒绝删除并返回原因；成功返回空字符串。"""
    usage = get_category_usage(category_id)
    if usage["sub_count"] > 0:
        return f"该分类下还有 {usage['sub_count']} 个小类，请先删除或移走它们"
    if usage["expense_count"] > 0:
        return (
            f"该分类下还有 {usage['expense_count']} 笔账目，不能删除。"
            "请先在「明细」页把这些账目改到其他分类"
        )
    conn = get_connection()
    try:
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()
    finally:
        conn.close()
    return ""


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


def get_parent_id(category_id: int) -> int | None:
    """查一个分类的上级大类 id（一级分类返回 None）。"""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT parent_id FROM categories WHERE id = ?", (category_id,)
        ).fetchone()
        return row["parent_id"] if row else None
    finally:
        conn.close()


# ---------- 账目读写 ----------


def insert_expense(
    amount_cents: int, category_id: int, date: str, note: str = "", kind: str = "expense"
) -> int:
    """新增一笔账，返回新账目 id。
    amount_cents：金额（单位：分）；date：格式 YYYY-MM-DD；kind：'expense' 或 'income'。"""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO expenses (amount_cents, category_id, date, note, kind) VALUES (?, ?, ?, ?, ?)",
            (amount_cents, category_id, date, note, kind),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_expenses_by_date(date: str) -> list[sqlite3.Row]:
    """某一天的全部账目（含分类名），按记录时间倒序。"""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT e.id, e.amount_cents, e.note, e.kind,
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


def search_expenses(
    keyword: str = "",
    date_from: str = "",
    date_to: str = "",
    top_id: int | None = None,
    sub_id: int | None = None,
    min_cents: int | None = None,
    max_cents: int | None = None,
    kind: str | None = None,
) -> list[sqlite3.Row]:
    """按条件搜索账目，按日期倒序。空条件 = 不过滤。"""
    sql = """
        SELECT e.id, e.date, e.amount_cents, e.note, e.kind,
               s.name AS sub_name, t.name AS top_name
        FROM expenses e
        JOIN categories s ON s.id = e.category_id
        LEFT JOIN categories t ON t.id = s.parent_id
        WHERE 1=1
    """
    params: list = []
    if keyword:
        like = f"%{keyword}%"
        sql += " AND (e.note LIKE ? OR s.name LIKE ? OR t.name LIKE ?)"
        params += [like, like, like]
    if date_from:
        sql += " AND e.date >= ?"
        params.append(date_from)
    if date_to:
        sql += " AND e.date <= ?"
        params.append(date_to)
    if sub_id is not None:
        sql += " AND e.category_id = ?"
        params.append(sub_id)
    elif top_id is not None:
        sql += " AND s.parent_id = ?"
        params.append(top_id)
    if min_cents is not None:
        sql += " AND e.amount_cents >= ?"
        params.append(min_cents)
    if max_cents is not None:
        sql += " AND e.amount_cents <= ?"
        params.append(max_cents)
    if kind is not None:
        sql += " AND e.kind = ?"
        params.append(kind)
    sql += " ORDER BY e.date DESC, e.created_at DESC, e.id DESC"
    conn = get_connection()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def get_expense(expense_id: int) -> sqlite3.Row:
    """取一笔账（编辑时用来回填表单）。"""
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    finally:
        conn.close()


def update_expense(
    expense_id: int,
    amount_cents: int,
    category_id: int,
    date: str,
    note: str = "",
    kind: str = "expense",
) -> None:
    """修改一笔账。"""
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE expenses SET amount_cents = ?, category_id = ?, date = ?, note = ?, kind = ? WHERE id = ?",
            (amount_cents, category_id, date, note, kind, expense_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_expense(expense_id: int) -> None:
    """删除一笔账。"""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
    finally:
        conn.close()


# ---------- 统计查询 ----------


def get_month_summary(month: str) -> sqlite3.Row:
    """某个月（格式 YYYY-MM）的支出、收入合计。"""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN kind='expense' THEN amount_cents END), 0) AS expense_cents,
                COALESCE(SUM(CASE WHEN kind='income' THEN amount_cents END), 0) AS income_cents
            FROM expenses
            WHERE substr(date, 1, 7) = ?
            """,
            (month,),
        ).fetchone()
    finally:
        conn.close()


def get_month_expense_by_top(month: str) -> list[sqlite3.Row]:
    """某个月的支出按一级大类汇总，从多到少排序。"""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT t.name AS top_name, SUM(e.amount_cents) AS total_cents
            FROM expenses e
            JOIN categories s ON s.id = e.category_id
            LEFT JOIN categories t ON t.id = s.parent_id
            WHERE e.kind = 'expense' AND substr(e.date, 1, 7) = ?
            GROUP BY t.id
            ORDER BY total_cents DESC
            """,
            (month,),
        ).fetchall()
    finally:
        conn.close()


def get_monthly_trend(months: int = 12, end_month: str = "") -> list[sqlite3.Row]:
    """最近 N 个月（截止 end_month，默认当月）的每月支出/收入合计，按月份升序。"""
    if not end_month:
        end_month = datetime.now().strftime("%Y-%m")
    y, m = map(int, end_month.split("-"))
    start_total = y * 12 + (m - 1) - (months - 1)
    start_y, start_m0 = divmod(start_total, 12)
    start_month = f"{start_y:04d}-{start_m0 + 1:02d}"
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT substr(date, 1, 7) AS month, kind, SUM(amount_cents) AS total_cents
            FROM expenses
            WHERE substr(date, 1, 7) BETWEEN ? AND ?
            GROUP BY month, kind
            ORDER BY month
            """,
            (start_month, end_month),
        ).fetchall()
    finally:
        conn.close()
