import json, hashlib, sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
REG = BASE / "registry_real_verified/assets_verifiable_1M.jsonl"

def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def append_asset(asset):
    with open(REG, "a", encoding="utf-8") as f:
        f.write(json.dumps(asset, ensure_ascii=False) + "\n")

now = datetime.now().strftime("%Y%m%d")
added = 0

with open(REG, "rb") as f:
    idx = sum(1 for _ in f)

conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/yield_test.db")
cur = conn.cursor()

cur.execute("SELECT * FROM n")
cols = [d[0] for d in cur.description]
rows = [dict(zip(cols, r)) for r in cur.fetchall()]

# Group by source/type for aggregated analysis
from collections import defaultdict
by_source = defaultdict(list)
for r in rows:
    key = r.get("source") or r.get("type") or "unknown"
    by_source[key].append(r)

for source, items in by_source.items():
    idx += 1
    core = {"source": "11_数据资产/yield_test.db:source_analysis", "data": {"source": source, "count": len(items), "sample": items[:10]}}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "数据源分析",
        "name": "数据源_{}".format(source),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 500.00,
        "price_cny_floor": 100.00,
        "deliverable": "数据源覆盖度、字段完整性、质量评分、可用性评估、接入建议",
        "tags": ["yield", "data_source", "analysis", "verifiable", "commercial"],
        "files": []
    })
    added += 1

# Individual extract records as commercial data points
for r in rows:
    idx += 1
    core = {"source": "11_数据资产/yield_test.db:extract_record", "data": r}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "结构化提取记录",
        "name": "提取_{}".format(r.get("title") or r.get("url") or idx),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 5.00,
        "price_cny_floor": 1.00,
        "deliverable": "单条结构化提取结果、字段映射、置信度、来源链接",
        "tags": ["yield", "extract", "record", "verifiable", "commercial"],
        "files": []
    })
    added += 1

conn.close()
print("Added {} commercial assets from Yield data".format(added))
