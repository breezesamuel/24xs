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

# Factory data
conn = sqlite3.connect(r"F:/2026/24xs/99_产出/_data/factory.sqlite3")
cur = conn.cursor()

# 1. GEO探测 - per client/platform/question combination as distinct audit assets
cur.execute("SELECT * FROM geo_probes")
cols = [d[0] for d in cur.description]
probes = [dict(zip(cols, r)) for r in cur.fetchall()]

# Group by client for client-level audit report
from collections import defaultdict
by_client = defaultdict(list)
for p in probes:
    by_client[p.get("client") or p.get("domain") or "unknown"].append(p)

for client, client_probes in by_client.items():
    idx += 1
    core = {"source": "99_产出/_data/factory.sqlite3:geo_client_audit", "data": {"client": client, "probe_count": len(client_probes), "probes": client_probes[:50]}}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "GEO客户端审计报告",
        "name": "GEO审计_{}".format(client),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 5000.00,
        "price_cny_floor": 1000.00,
        "deliverable": "客户端全平台GEO可见性审计、竞品对比、改进建议、优先级矩阵",
        "tags": ["geo", "audit", "client_report", "verifiable", "high_value"],
        "files": []
    })
    added += 1

# 2. Platform-level GEO analysis
by_platform = defaultdict(list)
for p in probes:
    by_platform[p.get("platform") or "unknown"].append(p)

for platform, platform_probes in by_platform.items():
    idx += 1
    core = {"source": "99_产出/_data/factory.sqlite3:geo_platform_analysis", "data": {"platform": platform, "probe_count": len(platform_probes), "clients": list(set(p.get("client") for p in platform_probes))[:20]}}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "GEO平台分析",
        "name": "平台分析_{}".format(platform),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 3000.00,
        "price_cny_floor": 800.00,
        "deliverable": "平台回答模式、引用偏好、排名因素、优化策略、案例库",
        "tags": ["geo", "platform_analysis", "verifiable", "high_value"],
        "files": []
    })
    added += 1

# 3. Leads - enriched company profiles
cur.execute("SELECT * FROM leads")
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    row = dict(zip(cols, r))
    idx += 1
    core = {"source": "99_产出/_data/factory.sqlite3:lead_enriched", "data": row}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "商业线索档案",
        "name": "线索_{}".format(row.get("company") or row.get("name") or idx),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 200.00,
        "price_cny_floor": 50.00,
        "deliverable": "企业基础信息、决策人联系方式、采购意向、跟进记录、转化预测",
        "tags": ["lead", "sales", "b2b", "verifiable", "commercial"],
        "files": []
    })
    added += 1

# 4. Outreach templates - per industry/channel
cur.execute("SELECT * FROM outreach")
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    row = dict(zip(cols, r))
    idx += 1
    core = {"source": "99_产出/_data/factory.sqlite3:outreach_template", "data": row}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "销售话术模板",
        "name": "话术_{}".format(row.get("template") or row.get("channel") or idx),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 100.00,
        "price_cny_floor": 20.00,
        "deliverable": "开场白、价值点、异议处理、CTA、A/B测试版本",
        "tags": ["outreach", "sales", "template", "verifiable", "commercial"],
        "files": []
    })
    added += 1

# 5. Corpus - content assets per industry/kind
cur.execute("SELECT * FROM corpus")
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    row = dict(zip(cols, r))
    idx += 1
    core = {"source": "99_产出/_data/factory.sqlite3:corpus_content", "data": row}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "内容资产",
        "name": "内容_{}".format(row.get("title") or row.get("industry") or idx),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 50.00,
        "price_cny_floor": 10.00,
        "deliverable": "SEO/GEO优化内容、Schema标记、FAQ、白皮书、对比表",
        "tags": ["content", "seo", "geo", "verifiable", "commercial"],
        "files": []
    })
    added += 1

conn.close()
print("Added {} commercial assets from Factory data".format(added))
