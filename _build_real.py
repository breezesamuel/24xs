# build real SKU registry from actual sources only
import json, hashlib, sqlite3
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real"
OUT.mkdir(exist_ok=True)

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def sha256_file(p):
    h = hashlib.sha256()
    try:
        with open(p,"rb") as f:
            for chunk in iter(lambda:f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except:
        return ""

assets = []
now = datetime.now().strftime("%Y%m%d")
idx = 0

# 1. enterprise profiles
try:
    with open(BASE / "assets" / "企业档案.json", "r", encoding="utf-8") as f:
        profs = json.load(f)
    for i, obj in enumerate(profs):
        idx += 1
        name = obj.get("name") or obj.get("企业名称") or f"entity_{i}"
        s = json.dumps(obj, ensure_ascii=False, sort_keys=True)
        assets.append({
            "asset_id": f"R-{now}-{idx:06d}",
            "type": "企业档案",
            "name": name,
            "source": "11_数据资产/assets/企业档案.json",
            "proof_type": "sha256",
            "proof": sha256_str(s),
            "files": [],
            "licensing": "internal-use-license-v1",
            "tags": ["entity","profile","b2b"],
            "price_cny_floor": 5.00,
            "price_cny_ref": 20.00,
            "deliverable": "完整JSON档案"
        })
except Exception as e:
    pass

# 2. html snapshots
for p in (BASE / "assets").glob("*.html"):
    idx += 1
    assets.append({
        "asset_id": f"R-{now}-{idx:06d}",
        "type": "网页快照",
        "name": p.stem,
        "source": str(p).replace("F:\\2026\\24xs\\",""),
        "proof_type": "sha256",
        "proof": sha256_file(p),
        "files": [str(p).replace("F:\\2026\\24xs\\","")],
        "licensing": "internal-use-license-v1",
        "tags": ["snapshot","html"],
        "price_cny_floor": 2.00,
        "price_cny_ref": 10.00,
        "deliverable": "HTML原始文件"
    })

# 3. CCGP notices
try:
    conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM notices")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        idx += 1
        row = dict(zip(cols, r))
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            "asset_id": f"R-{now}-{idx:06d}",
            "type": "招采公告",
            "name": (row.get("title") or row.get("TITLE") or f"notice_{row.get('rowid') or idx}")[:120],
            "source": "11_数据资产/ccgp_production.db:notices",
            "proof_type": "sha256",
            "proof": sha256_str(s),
            "files": [],
            "licensing": "internal-use-license-v1",
            "tags": ["ccgp","notice","b2b","procurement"],
            "price_cny_floor": 1.00,
            "price_cny_ref": 5.00,
            "deliverable": "结构化公告记录"
        })
    conn.close()
except Exception as e:
    pass

# 4. CCGP buyers
try:
    conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM buyers")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        idx += 1
        row = dict(zip(cols, r))
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            "asset_id": f"R-{now}-{idx:06d}",
            "type": "采购主体",
            "name": f"buyer_{row.get('rowid') or idx}",
            "source": "11_数据资产/ccgp_production.db:buyers",
            "proof_type": "sha256",
            "proof": sha256_str(s),
            "files": [],
            "licensing": "internal-use-license-v1",
            "tags": ["ccgp","buyer","b2b"],
            "price_cny_floor": 2.00,
            "price_cny_ref": 10.00,
            "deliverable": "采购主体结构化记录"
        })
    conn.close()
except Exception as e:
    pass

# 5. CCGP grid
try:
    conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM grid")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        idx += 1
        row = dict(zip(cols, r))
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            "asset_id": f"R-{now}-{idx:06d}",
            "type": "招采明细",
            "name": f"grid_{row.get('rowid') or idx}",
            "source": "11_数据资产/ccgp_production.db:grid",
            "proof_type": "sha256",
            "proof": sha256_str(s),
            "files": [],
            "licensing": "internal-use-license-v1",
            "tags": ["ccgp","grid","detail"],
            "price_cny_floor": 0.50,
            "price_cny_ref": 2.00,
            "deliverable": "明细结构化记录"
        })
    conn.close()
except Exception as e:
    pass

# 6. yield extract
try:
    conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/yield_test.db")
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM n")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        idx += 1
        row = dict(zip(cols, r))
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            "asset_id": f"R-{now}-{idx:06d}",
            "type": "抽取结果",
            "name": f"yield_{row.get('rowid') or idx}",
            "source": "11_数据资产/yield_test.db:n",
            "proof_type": "sha256",
            "proof": sha256_str(s),
            "files": [],
            "licensing": "internal-use-license-v1",
            "tags": ["extract","yield"],
            "price_cny_floor": 0.50,
            "price_cny_ref": 3.00,
            "deliverable": "抽取结构化记录"
        })
    conn.close()
except Exception as e:
    pass

# 7. factory: geo_probes
try:
    conn = sqlite3.connect(r"F:/2026/24xs/99_产出/_data/factory.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM geo_probes")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        idx += 1
        row = dict(zip(cols, r))
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            "asset_id": f"R-{now}-{idx:06d}",
            "type": "GEO探测",
            "name": f"probe_{row.get('rowid') or idx}",
            "source": "99_产出/_data/factory.sqlite3:geo_probes",
            "proof_type": "sha256",
            "proof": sha256_str(s),
            "files": [],
            "licensing": "internal-use-license-v1",
            "tags": ["geo","probe","audit"],
            "price_cny_floor": 5.00,
            "price_cny_ref": 20.00,
            "deliverable": "探测记录JSON"
        })
    conn.close()
except Exception as e:
    pass

# 8. factory: corpus
try:
    conn = sqlite3.connect(r"F:/2026/24xs/99_产出/_data/factory.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM corpus")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        idx += 1
        row = dict(zip(cols, r))
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            "asset_id": f"R-{now}-{idx:06d}",
            "type": "内容语料",
            "name": f"corpus_{row.get('rowid') or idx}",
            "source": "99_产出/_data/factory.sqlite3:corpus",
            "proof_type": "sha256",
            "proof": sha256_str(s),
            "files": [],
            "licensing": "internal-use-license-v1",
            "tags": ["content","corpus","geo"],
            "price_cny_floor": 10.00,
            "price_cny_ref": 50.00,
            "deliverable": "语料记录JSON"
        })
    conn.close()
except Exception as e:
    pass

# 9. factory: leads
try:
    conn = sqlite3.connect(r"F:/2026/24xs/99_产出/_data/factory.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM leads")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        idx += 1
        row = dict(zip(cols, r))
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            "asset_id": f"R-{now}-{idx:06d}",
            "type": "潜在客户线索",
            "name": f"lead_{row.get('rowid') or idx}",
            "source": "99_产出/_data/factory.sqlite3:leads",
            "proof_type": "sha256",
            "proof": sha256_str(s),
            "files": [],
            "licensing": "internal-use-license-v1",
            "tags": ["lead","b2b","sales"],
            "price_cny_floor": 20.00,
            "price_cny_ref": 100.00,
            "deliverable": "线索结构化记录"
        })
    conn.close()
except Exception as e:
    pass

# 10. factory: outreach
try:
    conn = sqlite3.connect(r"F:/2026/24xs/99_产出/_data/factory.sqlite3")
    cur = conn.cursor()
    cur.execute("SELECT rowid, * FROM outreach")
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        idx += 1
        row = dict(zip(cols, r))
        s = json.dumps(row, ensure_ascii=False, sort_keys=True)
        assets.append({
            "asset_id": f"R-{now}-{idx:06d}",
            "type": "触达文案",
            "name": f"outreach_{row.get('rowid') or idx}",
            "source": "99_产出/_data/factory.sqlite3:outreach",
            "proof_type": "sha256",
            "proof": sha256_str(s),
            "files": [],
            "licensing": "internal-use-license-v1",
            "tags": ["outreach","copy","sales"],
            "price_cny_floor": 5.00,
            "price_cny_ref": 20.00,
            "deliverable": "文案记录JSON"
        })
    conn.close()
except Exception as e:
    pass

# write
with open(OUT / "assets_registry_real.jsonl", "w", encoding="utf-8") as f:
    for a in assets:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")

# sku list
skus = [{"sku_id":a["asset_id"],"name":a["name"][:80],"type":a["type"],"price_cny_ref":a["price_cny_ref"],"proof":a["proof"][:16]+"..."} for a in assets]
with open(OUT / "sku_list_real.json", "w", encoding="utf-8") as f:
    json.dump(skus, f, ensure_ascii=False, indent=2)

# manifest
manifest = {
    "total": len(assets),
    "format": "jsonl",
    "path": "11_数据资产/registry_real/assets_registry_real.jsonl",
    "license": "internal-use-license-v1",
    "created_at": datetime.utcnow().isoformat() + "Z"
}
with open(OUT / "manifest_real.json", "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f"total_real={len(assets)}")
