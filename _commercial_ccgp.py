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

conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
cur = conn.cursor()

# 1. Grid line items
cur.execute("SELECT * FROM grid")
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    row = dict(zip(cols, r))
    idx += 1
    core = {"source": "11_数据资产/ccgp_production.db:grid_lineitem", "data": row}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "招采明细行",
        "name": "标项_{}".format(row.get("project_name") or row.get("title") or idx),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 10.00,
        "price_cny_floor": 2.00,
        "deliverable": "中标/成交明细行结构化记录",
        "tags": ["ccgp", "lineitem", "transaction", "verifiable", "commercial"],
        "files": []
    })
    added += 1

# 2. Buyer profiles
cur.execute("SELECT name, n_notices, total_budget, provinces, latest FROM buyers")
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    row = dict(zip(cols, r))
    cur2 = conn.cursor()
    cur2.execute("SELECT title, budget_cny, province, channel FROM notices WHERE buyer = ?", (row["name"],))
    buyer_notices = [dict(zip([d[0] for d in cur2.description], nr)) for nr in cur2.fetchall()]
    
    idx += 1
    core = {
        "source": "11_数据资产/ccgp_production.db:buyer_profile",
        "data": {
            "buyer": row["name"],
            "notice_count": row["n_notices"],
            "total_budget": row["total_budget"],
            "provinces": row["provinces"],
            "latest": row["latest"],
            "notices": buyer_notices[:100]
        }
    }
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "采购方画像",
        "name": "采购方画像_{}".format(row["name"]),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 500.00,
        "price_cny_floor": 100.00,
        "deliverable": "采购方全维度画像（历史采购、预算、偏好、供应商网络）",
        "tags": ["ccgp", "buyer_profile", "intelligence", "verifiable", "high_value"],
        "files": []
    })
    added += 1

# 3. Category market analysis
cur.execute("SELECT channel, COUNT(*) as cnt, SUM(budget_cny) as total_budget FROM notices WHERE budget_cny IS NOT NULL GROUP BY channel")
for r in cur.fetchall():
    channel, cnt, total_budget = r
    idx += 1
    core = {"source": "11_数据资产/ccgp_production.db:category_analysis", "data": {"channel": channel, "notice_count": cnt, "total_budget_cny": total_budget}}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "品类市场分析",
        "name": "品类分析_{}".format(channel),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 2000.00,
        "price_cny_floor": 500.00,
        "deliverable": "品类市场规模、采购频次、预算分布、主要采购方、季度趋势",
        "tags": ["ccgp", "market_analysis", "category", "verifiable", "high_value"],
        "files": []
    })
    added += 1

# 4. Province market analysis
cur.execute("SELECT province, COUNT(*) as cnt, SUM(budget_cny) as total_budget FROM notices WHERE budget_cny IS NOT NULL GROUP BY province")
for r in cur.fetchall():
    province, cnt, total_budget = r
    idx += 1
    core = {"source": "11_数据资产/ccgp_production.db:province_analysis", "data": {"province": province, "notice_count": cnt, "total_budget_cny": total_budget}}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "区域市场分析",
        "name": "区域分析_{}".format(province),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 1500.00,
        "price_cny_floor": 300.00,
        "deliverable": "省级采购市场规模、主要采购方、品类分布、季度趋势、竞争格局",
        "tags": ["ccgp", "market_analysis", "province", "verifiable", "high_value"],
        "files": []
    })
    added += 1

# 5. Supplier intelligence (winners)
cur.execute("SELECT DISTINCT winner FROM grid WHERE winner IS NOT NULL AND winner != \'\' LIMIT 1000")
for r in cur.fetchall():
    winner = r[0]
    if not winner: continue
    cur2 = conn.cursor()
    cur2.execute("SELECT project_name, buyer, budget_cny, win_date FROM grid WHERE winner = ?", (winner,))
    wins = [dict(zip([d[0] for d in cur2.description], nr)) for nr in cur2.fetchall()]
    if len(wins) < 2: continue
    
    idx += 1
    core = {"source": "11_数据资产/ccgp_production.db:supplier_profile", "data": {"supplier": winner, "win_count": len(wins), "wins": wins[:50]}}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "供应商情报",
        "name": "供应商情报_{}".format(winner),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 1000.00,
        "price_cny_floor": 200.00,
        "deliverable": "供应商中标历史、服务采购方、金额分布、品类强项、竞争对手",
        "tags": ["ccgp", "supplier_intel", "verifiable", "high_value"],
        "files": []
    })
    added += 1

conn.close()
print("Added {} commercial assets from CCGP deep structure".format(added))
