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

# yield_test.db: n
try:
    conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/yield_test.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM n")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        row = dict(zip(cols,r))
        idx += 1
        core = {"source": "11_数据资产/yield_test.db:n", "data": row}
        proof = sha256_str(json.dumps(core, sort_keys=True, ensure_ascii=False))
        assets.append({
            "asset_id": f"V-{now}-{idx:06d}",
            "type": "抽取结果",
            "name": f"yield_{row.get('rowid') or idx}",
            "source": core["source"],
            "proof": proof,
            "proof_type": "sha256",
            "price_cny_ref": 3.00,
            "price_cny_floor": 0.50,
            "deliverable": "结构化记录",
            "tags": ["extract", "verifiable"],
            "files": []
        })
    conn.close()
except Exception as e:
    pass

# factory.sqlite3: geo_probes, corpus, leads, outreach
try:
    conn = sqlite3.connect(r"F:/2026/24xs/99_产出/_data/factory.sqlite3")
    cur = conn.cursor()
    for table, type_name, price_ref, price_floor in [
        ("geo_probes", "GEO探测", 20.00, 5.00),
        ("corpus", "内容语料", 50.00, 10.00),
        ("leads", "潜在客户线索", 100.00, 20.00),
        ("outreach", "触达文案", 20.00, 5.00)
    ]:
        try:
            cur.execute("SELECT * FROM " + table)
            cols = [d[0] for d in cur.description]
            for r in cur.fetchall():
                row = dict(zip(cols,r))
                idx += 1
                core = {"source": f"99_产出/_data/factory.sqlite3:{table}", "data": row}
                proof = sha256_str(json.dumps(core, sort_keys=True, ensure_ascii=False))
                assets.append({
                    "asset_id": f"V-{now}-{idx:06d}",
                    "type": type_name,
                    "name": f"{type_name}_{row.get('rowid') or idx}",
                    "source": core["source"],
                    "proof": proof,
                    "proof_type": "sha256",
                    "price_cny_ref": price_ref,
                    "price_cny_floor": price_floor,
                    "deliverable": "结构化记录",
                    "tags": [type_name, "verifiable"],
                    "files": []
                })
        except Exception as e:
            pass
    conn.close()
except Exception as e:
    pass

with open(OUT / "assets_verifiable.jsonl", "w", encoding="utf-8") as f:
    for a in assets:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
print(len(assets))
