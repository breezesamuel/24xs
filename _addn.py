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

conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
cur = conn.cursor()
cur.execute("SELECT rowid, title, buyer, budget, budget_cny FROM notices")
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    row = dict(zip(cols,r))
    idx += 1
    core = {"name": row.get("title"), "source": "11_数据资产/ccgp_production.db:notices", "data": row}
    proof = sha256_str(json.dumps(core, sort_keys=True, ensure_ascii=False))
    assets.append({
        "asset_id": f"V-{now}-{idx:06d}",
        "type": "招采公告",
        "name": (row.get("title") or "")[:80],
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 5.00,
        "price_cny_floor": 1.00,
        "deliverable": "结构化记录",
        "tags": ["ccgp", "verifiable"],
        "files": []
    })
conn.close()

with open(OUT / "assets_verifiable.jsonl", "w", encoding="utf-8") as f:
    for a in assets:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
print(len(assets))
