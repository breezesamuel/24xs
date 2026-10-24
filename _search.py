import json, sqlite3
from pathlib import Path

p = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified/assets_verifiable_1M.jsonl")
OUT = Path(r"F:/2026/24xs/11_数据资产/registry_real_verified")
OUT.mkdir(exist_ok=True)

# Create SQLite FTS5 index
db = OUT / "assets_search.db"
conn = sqlite3.connect(db)
cur = conn.cursor()

cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS assets_fts USING fts5(
        asset_id, name, type, tags, source, content=""
    )
""")

# Index in batches
batch = []
with open(p, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        a = json.loads(line)
        tags = " ".join(a.get("tags", []))
        batch.append((a["asset_id"], a["name"], a["type"], tags, a["source"]))
        if len(batch) >= 10000:
            cur.executemany("INSERT INTO assets_fts VALUES (?,?,?,?,?)", batch)
            batch = []
            if i % 200000 == 0:
                print("indexed", i)
    if batch:
        cur.executemany("INSERT INTO assets_fts VALUES (?,?,?,?,?)", batch)

conn.commit()
conn.close()
print("Search index built")
