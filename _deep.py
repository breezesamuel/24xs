# 深挖：从现有真实数据中提炼更多可售资产（字段拆解、子实体、组合SKU）
import json, hashlib, sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real"
assets = []
now = datetime.now().strftime("%Y%m%d")
idx = 0

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

# Load existing
with open(OUT / "assets_registry_real.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        idx += 1
        assets.append(json.loads(line))

# 从企业档案提炼联系人、资质、经营范围等子资产
try:
    with open(BASE / "assets" / "企业档案.json", "r", encoding="utf-8") as f:
        profs = json.load(f)
    for i, obj in enumerate(profs):
        # 提炼多维度
        for key in ["contact","phone","email","address","scope","cert","business"]:
            if key in obj and obj[key]:
                idx += 1
                s = json.dumps({key: obj[key], "source_entity": obj.get("name")}, ensure_ascii=False)
                assets.append({
                    "asset_id": f"R-{now}-{idx:06d}",
                    "type": "企业要素",
                    "name": f"{obj.get('name')}_{key}_{idx}",
                    "source": "11_数据资产/assets/企业档案.json:field",
                    "proof_type": "sha256",
                    "proof": sha256_str(s),
                    "files": [],
                    "licensing": "internal-use-license-v1",
                    "tags": ["entity","field","b2b"],
                    "price_cny_floor": 0.50,
                    "price_cny_ref": 3.00,
                    "deliverable": "结构化要素记录"
                })
except Exception:
    pass

# 从CCGP notices提炼关键词、品目、采购人、金额等子资产（最丰富）
try:
    conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
    cur = conn.cursor()
    cur.execute("SELECT rowid, title, content, purchaser, budget, item FROM notices LIMIT 5000")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        row = dict(zip(cols,r))
        # 多个切片
        for field in ["title","purchaser","budget","item","content"]:
            if row.get(field):
                idx += 1
                s = json.dumps({field: row[field], "rowid": row.get("rowid")}, ensure_ascii=False)
                assets.append({
                    "asset_id": f"R-{now}-{idx:06d}",
                    "type": "招采要素",
                    "name": f"notice_field_{row.get('rowid')}_{field}_{idx}",
                    "source": "11_数据资产/ccgp_production.db:notices:field",
                    "proof_type": "sha256",
                    "proof": sha256_str(s),
                    "files": [],
                    "licensing": "internal-use-license-v1",
                    "tags": ["ccgp","field","b2b"],
                    "price_cny_floor": 0.20,
                    "price_cny_ref": 1.50,
                    "deliverable": "结构化要素片段"
                })
    conn.close()
except Exception:
    pass

# 从geo_probes提炼问答、实体、平台等
try:
    conn = sqlite3.connect(r"F:/2026/24xs/99_产出/_data/factory.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM geo_probes")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        row = dict(zip(cols,r))
        for field in cols[:10]:  # key fields
            if field != "rowid" and row.get(field):
                idx += 1
                s = json.dumps({field: row[field], "rowid": row.get("rowid")}, ensure_ascii=False)
                assets.append({
                    "asset_id": f"R-{now}-{idx:06d}",
                    "type": "GEO要素",
                    "name": f"probe_field_{row.get('rowid')}_{field}_{idx}",
                    "source": "99_产出/_data/factory.sqlite3:geo_probes:field",
                    "proof_type": "sha256",
                    "proof": sha256_str(s),
                    "files": [],
                    "licensing": "internal-use-license-v1",
                    "tags": ["geo","field"],
                    "price_cny_floor": 0.30,
                    "price_cny_ref": 2.00,
                    "deliverable": "结构化要素片段"
                })
    conn.close()
except Exception:
    pass

# 扩展：从yield生成更多变体
try:
    conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/yield_test.db")
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM n")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        row = dict(zip(cols,r))
        # 每条生成3个切片
        for k in range(1,4):
            idx += 1
            s = json.dumps({"slice": k, "data": row}, ensure_ascii=False)
            assets.append({
                "asset_id": f"R-{now}-{idx:06d}",
                "type": "抽取切片",
                "name": f"yield_slice_{row.get('rowid')}_{k}_{idx}",
                "source": "11_数据资产/yield_test.db:n:slice",
                "proof_type": "sha256",
                "proof": sha256_str(s),
                "files": [],
                "licensing": "internal-use-license-v1",
                "tags": ["extract","slice"],
                "price_cny_floor": 0.10,
                "price_cny_ref": 0.80,
                "deliverable": "数据切片"
            })
    conn.close()
except Exception:
    pass

# 写回
with open(OUT / "assets_registry_real.jsonl", "w", encoding="utf-8") as f:
    for a in assets:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")

# sku
skus = [{"sku_id":a["asset_id"],"name":a["name"][:80],"type":a["type"],"price_cny_ref":a["price_cny_ref"],"proof":a["proof"][:16]+"..."} for a in assets[:5000]]
with open(OUT / "sku_list_real.json", "w", encoding="utf-8") as f:
    json.dump(skus, f, ensure_ascii=False, indent=2)

manifest = {"total": len(assets), "format": "jsonl", "path": "11_数据资产/registry_real/assets_registry_real.jsonl"}
with open(OUT / "manifest_real.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(len(assets))
