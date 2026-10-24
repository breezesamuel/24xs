import json, hashlib, sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
assets = []
with open(OUT / "assets_verifiable.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        assets.append(json.loads(line))

idx = len(assets)
now = datetime.now().strftime("%Y%m%d")
def sha256_str(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()

# buyers
conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
cur = conn.cursor()
cur.execute("SELECT name, n_notices, total_budget, provinces, latest FROM buyers")
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    row = dict(zip(cols,r))
    idx += 1
    core = {"name": row.get("name"), "source": "11_数据资产/ccgp_production.db:buyers", "data": row}
    proof = sha256_str(json.dumps(core, sort_keys=True, ensure_ascii=False))
    assets.append({
        "asset_id": f"V-{now}-{idx:06d}",
        "type": "采购主体",
        "name": (row.get("name") or "")[:80],
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 10.00,
        "price_cny_floor": 2.00,
        "deliverable": "结构化记录",
        "tags": ["ccgp", "buyer", "verifiable"],
        "files": []
    })
# grid
cur.execute("SELECT * FROM grid")
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    row = dict(zip(cols,r))
    idx += 1
    core = {"source": "11_数据资产/ccgp_production.db:grid", "data": row}
    proof = sha256_str(json.dumps(core, sort_keys=True, ensure_ascii=False))
    assets.append({
        "asset_id": f"V-{now}-{idx:06d}",
        "type": "招采明细",
        "name": f"grid_{row.get('rowid') or idx}",
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 2.00,
        "price_cny_floor": 0.50,
        "deliverable": "结构化记录",
        "tags": ["ccgp", "grid", "verifiable"],
        "files": []
    })
conn.close()

with open(OUT / "assets_verifiable.jsonl", "w", encoding="utf-8") as f:
    for a in assets:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
print(len(assets))
