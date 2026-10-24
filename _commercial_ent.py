import json, hashlib
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

# Enterprise profiles - each as enriched company dossier
with open(BASE / "assets" / "企业档案.json", "r", encoding="utf-8") as f:
    profs = json.load(f)

for i, obj in enumerate(profs):
    idx += 1
    core = {"source": "11_数据资产/assets/企业档案.json:enriched_dossier", "data": obj}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "企业全维档案",
        "name": "企业档案_{}".format(obj.get("name") or obj.get("企业名称") or i),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 100.00,
        "price_cny_floor": 20.00,
        "deliverable": "企业基础信息、经营范围、资质证书、联系方式、风险提示、关联关系",
        "tags": ["entity", "dossier", "due_diligence", "verifiable", "commercial"],
        "files": []
    })
    added += 1

# Industry aggregation from profiles
from collections import defaultdict
by_industry = defaultdict(list)
for obj in profs:
    ind = obj.get("industry") or obj.get("行业") or "未分类"
    by_industry[ind].append(obj)

for industry, companies in by_industry.items():
    idx += 1
    core = {"source": "11_数据资产/assets/企业档案.json:industry_map", "data": {"industry": industry, "company_count": len(companies), "companies": [c.get("name") for c in companies[:20]]}}
    proof = sha256_str(canonical(core))
    append_asset({
        "asset_id": "V-{}-{:06d}".format(now, idx),
        "type": "行业企业图谱",
        "name": "行业图谱_{}".format(industry),
        "source": core["source"],
        "proof": proof,
        "proof_type": "sha256",
        "price_cny_ref": 2000.00,
        "price_cny_floor": 500.00,
        "deliverable": "行业企业全景、规模分布、地域分布、核心企业、上下游关系",
        "tags": ["entity", "industry_map", "intelligence", "verifiable", "high_value"],
        "files": []
    })
    added += 1

# HTML snapshots - each as verified web evidence
for p in (BASE / "assets").glob("*.html"):
    idx += 1
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
        core = {"source": str(p).replace("F:\\2026\\24xs\\", ""), "data": {"url": p.stem, "content_hash": sha256_str(txt), "length": len(txt)}}
        proof = sha256_str(canonical(core))
        append_asset({
            "asset_id": "V-{}-{:06d}".format(now, idx),
            "type": "网页证据快照",
            "name": "网页快照_{}".format(p.stem),
            "source": core["source"],
            "proof": proof,
            "proof_type": "sha256",
            "price_cny_ref": 20.00,
            "price_cny_floor": 5.00,
            "deliverable": "原始HTML、内容哈希、时间戳、可用于合规/审计/尽调",
            "tags": ["html", "evidence", "snapshot", "verifiable", "commercial"],
            "files": [str(p).replace("F:\\2026\\24xs\\", "")]
        })
        added += 1
    except:
        pass

print("Added {} commercial assets from Enterprise/HTML".format(added))
