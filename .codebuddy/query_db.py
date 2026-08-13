"""脚本：查看 SQLite 数据库的表结构和数据记录
用法: python .codebuddy/query_db.py [db_type] [date]
  db_type: news (默认) | rss
  date: 2026-08-12 (默认最新)
"""
import sqlite3
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 解析参数
db_type = sys.argv[1] if len(sys.argv) > 1 else 'news'
date = sys.argv[2] if len(sys.argv) > 2 else None

# 自动找最新的 db 文件
if date is None:
    sub_dir = os.path.join(BASE, 'output', db_type)
    if not os.path.isdir(sub_dir):
        print(f"目录不存在: {sub_dir}")
        sys.exit(1)
    db_files = sorted([f for f in os.listdir(sub_dir) if f.endswith('.db')], reverse=True)
    if not db_files:
        print(f"没有找到 .db 文件: {sub_dir}")
        sys.exit(1)
    date = db_files[0].replace('.db', '')

db_path = os.path.join(BASE, 'output', db_type, f'{date}.db')
if not os.path.exists(db_path):
    print(f"数据库不存在: {db_path}")
    sys.exit(1)

print("=" * 60)
print(f"[{db_type.upper()} DB] {date}.db")
print(f"路径: {db_path}")
print("=" * 60)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [r[0] for r in cur.fetchall()]

for t in tables:
    print(f"\n--- 表: {t} ---")
    # 列信息
    cur.execute(f'PRAGMA table_info("{t}")')
    cols = cur.fetchall()
    print("  列:")
    for c in cols:
        pk = " [PK]" if c[5] else ""
        print(f"    - {c[1]} ({c[2]}){pk}")
    # 行数
    cur.execute(f'SELECT COUNT(*) FROM "{t}"')
    count = cur.fetchone()[0]
    print(f"  记录数: {count}")

    # 如果记录数 <= 10，直接显示
    if 0 < count <= 10:
        cur.execute(f'SELECT * FROM "{t}" LIMIT 10')
        rows = cur.fetchall()
        col_names = [c[1] for c in cols]
        print(f"  数据:")
        for row in rows:
            # 用 ascii 安全方式打印
            d = dict(zip(col_names, row))
            safe_d = {}
            for k, v in d.items():
                if isinstance(v, str):
                    safe_d[k] = v.encode('ascii', errors='replace').decode('ascii')
                else:
                    safe_d[k] = v
            print(f"    {safe_d}")

# 显示前 5 条主数据
if db_type == 'news':
    cur.execute("SELECT id, title, platform_id, rank, last_crawl_time FROM news_items ORDER BY last_crawl_time DESC LIMIT 5")
elif db_type == 'rss':
    cur.execute("SELECT id, title, feed_id, published_at, last_crawl_time FROM rss_items ORDER BY last_crawl_time DESC LIMIT 5")
else:
    cur.close()
    conn.close()
    sys.exit(0)

rows = cur.fetchall()
if rows:
    print(f"\n--- 最近 5 条数据 ---")
    col_desc = [d[0] for d in cur.description]
    for row in rows:
        parts = []
        for i, val in enumerate(row):
            s = str(val)
            if isinstance(val, str):
                s = s[:60]
            parts.append(f"{col_desc[i]}={s}")
        safe = ' | '.join(parts).encode('ascii', errors='replace').decode('ascii')
        print(f"  {safe}")

conn.close()
print("\nDone!")
