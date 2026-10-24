# -*- coding: utf-8 -*-
"""SQLite 数据层。所有业务数据落库，便于复盘、归因与对账。零外部依赖。"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    cmd TEXT NOT NULL,
    detail TEXT
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    industry TEXT,
    contact TEXT,
    tier TEXT,
    status TEXT DEFAULT 'prospect',
    created_ts TEXT
);

CREATE TABLE IF NOT EXISTS geo_probes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    client TEXT,
    industry TEXT,
    platform TEXT,
    intent TEXT,
    question TEXT,
    mentioned INTEGER DEFAULT 0,
    rank_pos INTEGER DEFAULT 0,
    source_note TEXT
);
CREATE INDEX IF NOT EXISTS idx_probe ON geo_probes(client, ts);

CREATE TABLE IF NOT EXISTS corpus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    industry TEXT,
    kind TEXT,
    title TEXT,
    path TEXT,
    word_count INTEGER
);
CREATE INDEX IF NOT EXISTS idx_corpus ON corpus(industry, kind);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    company TEXT,
    industry TEXT,
    city TEXT,
    channel TEXT,
    contact TEXT,
    icp_score REAL,
    tier TEXT,
    pain TEXT,
    angle TEXT,
    status TEXT DEFAULT 'new',
    first_touch_ts TEXT,
    reply INTEGER DEFAULT 0,
    deal_cny REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_leads ON leads(industry, status);

CREATE TABLE IF NOT EXISTS outreach (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    lead_id INTEGER,
    channel TEXT,
    template TEXT,
    status TEXT DEFAULT 'queued',
    reply INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS money_in (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    client TEXT,
    item TEXT,
    amount REAL,
    kind TEXT DEFAULT 'income',
    note TEXT
);

CREATE TABLE IF NOT EXISTS money_out (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT,
    item TEXT,
    amount REAL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day TEXT,
    phase TEXT,
    title TEXT,
    owner TEXT,
    cny_target REAL DEFAULT 0,
    done INTEGER DEFAULT 0,
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks ON tasks(day);
"""

# 幂等性迁移：leads.company 原本没有唯一约束，导致 `cli.py all` 每跑一次
# 就把同一批公司再插一遍（重复线索、重复触达、看板数字虚高）。
# 顺序很重要：先清历史重复，再建唯一索引，否则建索引会因冲突失败。
MIGRATIONS = [
    # leads：同公司只保留 id 最小的一条
    """
    DELETE FROM leads WHERE id NOT IN (
        SELECT MIN(id) FROM leads WHERE TRIM(COALESCE(company,'')) <> '' GROUP BY company
    ) AND TRIM(COALESCE(company,'')) <> ''
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_company
        ON leads(company) WHERE TRIM(COALESCE(company,'')) <> ''
    """,
    # verified：区分「真实主体」和「模板画像」。
    # PROSPECTS 里的 "{city}外贸工厂（自有品牌）" 这类是**待检索的画像**，
    # 不是公司。历史版本把画像当公司写进 leads，export_list 又把它们当 A 档
    # 名单导出，于是 60 条触达队列里 45 条是虚构的、无触达对象。
    # 加这一列后，画像只能进"假设池"，进不了触达队列。
    # 由 _ensure_column 幂等执行：ALTER TABLE ADD COLUMN 重复跑会报
    # "duplicate column name"，而 init() 只捕获 IntegrityError，会导致
    # 每次 `cli.py all` 都崩。所以这里不放进 MIGRATIONS。
    ("__add_column__", "leads", "verified", "INTEGER DEFAULT 0"),
    ("__index__", "idx_leads_verified", "ON leads(verified, tier)"),
    # outreach：同一线索 + 渠道 + 模板只排一次
    """
    DELETE FROM outreach WHERE id NOT IN (
        SELECT MIN(id) FROM outreach GROUP BY lead_id, channel, template
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_outreach_lead
        ON outreach(lead_id, channel, template)
    """,
    # geo_probes：同一客户 + 平台 + 问法只采一次（重跑不重复计采样量）
    """
    DELETE FROM geo_probes WHERE id NOT IN (
        SELECT MIN(id) FROM geo_probes
        GROUP BY COALESCE(client,''), COALESCE(platform,''), COALESCE(question,'')
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_probe_dedupe
        ON geo_probes(client, platform, question)
    """,
    # corpus：同一行业 + 类型 + 标题只登记一次
    """
    DELETE FROM corpus WHERE id NOT IN (
        SELECT MIN(id) FROM corpus GROUP BY COALESCE(industry,''), COALESCE(kind,''), COALESCE(title,'')
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_corpus_dedupe
        ON corpus(industry, kind, title)
    """,
]


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


@contextmanager
def conn():
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)
        # 迁移按顺序执行：先清重复再建唯一索引。
        # 之前这里 except IntegrityError: pass 会把"索引建不上"静默吞掉，
        # 结果重复数据照旧累积。现在把失败暴露出来。
        for i, sql in enumerate(MIGRATIONS):
            # 结构化迁移：加列 / 建索引。用「先查 sqlite_master 再决定」实现幂等，
            # 因为 ALTER TABLE ADD COLUMN 第二次执行会抛 duplicate column，
            # 而下面只捕获 IntegrityError，会让每次 cli.py all 都崩。
            if isinstance(sql, tuple):
                kind = sql[0]
                if kind == "__add_column__":
                    _, table, column, decl = sql
                    if not _has_column(c, table, column):
                        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
                elif kind == "__index__":
                    _, index, on_clause = sql
                    if not _has_index(c, index):
                        c.execute(f"CREATE INDEX IF NOT EXISTS {index} {on_clause}")
                continue
            try:
                c.execute(sql)
            except sqlite3.IntegrityError as e:
                raise RuntimeError(
                    f"db 迁移 #{i} 失败（唯一索引与现存数据冲突）: {sql.strip()[:60]}... -> {e}"
                ) from e


def _has_column(c: sqlite3.Connection, table: str, column: str) -> bool:
    return any(r["name"] == column for r in c.execute(f"PRAGMA table_info({table})"))


def _has_index(c: sqlite3.Connection, index: str) -> bool:
    return c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (index,)
    ).fetchone() is not None


def log_run(cmd: str, detail: str = "") -> None:
    with conn() as c:
        c.execute("INSERT INTO runs(ts, cmd, detail) VALUES (?,?,?)", (now(), cmd, detail))


def q(sql: str, args: tuple = ()) -> list[sqlite3.Row]:
    with conn() as c:
        return c.execute(sql, args).fetchall()


def scalar(sql: str, args: tuple = (), default=0):
    r = q(sql, args)
    if not r:
        return default
    v = r[0][0]
    return default if v is None else v


if __name__ == "__main__":
    init()
    tables = [r["name"] for r in q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    print("db :", DB_PATH)
    print("tables:", ", ".join(tables))
