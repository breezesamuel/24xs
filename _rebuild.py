# rebuild real assets with self-contained verifiable proofs (hash of canonical content)
import json, hashlib
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
OUT = BASE / "registry_real_verified"
OUT.mkdir(exist_ok=True)

def canonical(obj):
    # canonical JSON (sorted keys, no spaces, ensure_ascii)
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

assets = []
now = datetime.now().strftime("%Y%m%d")
idx = 0

# 1. enterprise profiles
try:
    with open(BASE / "assets" / "企业档案.json", "r", encoding="utf-8") as f:
        profs = json.load(f)
    for i, obj in enumerate(profs):
        idx += 1
        core = {
            "name": obj.get("name") or obj.get("企业名称"),
            "source": "11_数据资产/assets/企业档案.json",
            "data": obj
        }
        proof = sha256_str(canonical(core))
        assets.append({
            "asset_id": f"V-{now}-{idx:06d}",
            "type": "企业档案",
            "name": core["name"] or f"entity_{i}",
            "source": core["source"],
            "canonical": canonical(core),
            "proof_type": "sha256",
            "proof": proof,
            "files": [],
            "licensing": "internal-use-license-v1",
            "tags": ["entity","profile","verifiable"],
            "price_cny_floor": 5.00,
            "price_cny_ref": 20.00,
            "deliverable": "完整JSON档案"
        })
except Exception:
    pass

print("built", idx)
