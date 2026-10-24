# Ingestion pipeline: add new assets from sources, append to registry with proofs
import json, hashlib, sqlite3, os
from pathlib import Path
from datetime import datetime

BASE = Path(r"F:/2026/24xs/11_数据资产")
REG = BASE / "registry_real_verified/assets_verifiable_1M.jsonl"
STATE = BASE / "registry_real_verified/ingest_state.json"

def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def sha256_str(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"ccgp_notices_max_rowid": 0, "factory_probes_max_rowid": 0, "last_run": None}

def save_state(s):
    s["last_run"] = datetime.utcnow().isoformat() + "Z"
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")

def append_asset(asset):
    with open(REG, "a", encoding="utf-8") as f:
        f.write(json.dumps(asset, ensure_ascii=False) + "\n")

state = load_state()
now = datetime.now().strftime("%Y%m%d")
added = 0

# 1. CCGP new notices
try:
    conn = sqlite3.connect(r"F:/2026/24xs/11_数据资产/ccgp_production.db")
    cur = conn.cursor()
    last = state.get("ccgp_notices_max_rowid", 0)
    cur.execute("SELECT rowid, title, buyer, budget, budget_cny FROM notices WHERE rowid > ?", (last,))
    for row in cur.fetchall():
        rowid, title, buyer, budget, budget_cny = row
        core = {"name": title, "source": "11_数据资产/ccgp_production.db:notices", "data": {"rowid": rowid, "title": title, "buyer": buyer, "budget": budget, "budget_cny": budget_cny}}
        proof = sha256_str(canonical(core))
        append_asset({
            "asset_id": f"V-{now}-{rowid:06d}",
            "type": "招采公告",
            "name": (title or "")[:80],
            "source": core["source"],
            "proof": proof,
            "proof_type": "sha256",
            "price_cny_ref": 5.00,
            "price_cny_floor": 1.00,
            "deliverable": "结构化记录",
            "tags": ["ccgp", "verifiable", "auto_ingested"],
            "files": []
        })
        added += 1
        state["ccgp_notices_max_rowid"] = max(state.get("ccgp_notices_max_rowid", 0), rowid)
    conn.close()
except Exception as e:
    pass

# 2. Factory new probes
try:
    conn = sqlite3.connect(r"F:/2026/24xs/99_产出/_data/factory.sqlite3")
    cur = conn.cursor()
    last = state.get("factory_probes_max_rowid", 0)
    cur.execute("SELECT rowid, * FROM geo_probes WHERE rowid > ?", (last,))
    cols = [d[0] for d in cur.description]
    for r in cur.fetchall():
        row = dict(zip(cols, r))
        core = {"source": "99_产出/_data/factory.sqlite3:geo_probes", "data": row}
        proof = sha256_str(canonical(core))
        append_asset({
            "asset_id": f"V-{now}-{row.get("rowid"):06d}",
            "type": "GEO探测",
            "name": f"GEO探测_{row.get("rowid")}",
            "source": core["source"],
            "proof": proof,
            "proof_type": "sha256",
            "price_cny_ref": 20.00,
            "price_cny_floor": 5.00,
            "deliverable": "结构化记录",
            "tags": ["geo", "verifiable", "auto_ingested"],
            "files": []
        })
        added += 1
        state["factory_probes_max_rowid"] = max(state.get("factory_probes_max_rowid", 0), row.get("rowid", 0))
    conn.close()
except Exception as e:
    pass

save_state(state)
print(f"Added {added} new real assets")
