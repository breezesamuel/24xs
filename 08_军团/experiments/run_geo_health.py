# -*- coding: utf-8 -*-
"""对已核实归属的官网批量跑免费 GEO 体检，产出报告 + 敲门砖文案。

只跑 status=ok 的域名；mismatch/unreachable/needs_review 的 fail-closed 跳过。
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, r"F:\2026\24xs\01_引擎")
import geo_health as H  # noqa: E402

OUT = Path(r"F:\2026\24xs\99_产出\GEO体检报告")
OUT.mkdir(parents=True, exist_ok=True)

VER = Path(r"F:\2026\24xs\99_产出\获客名单\域名归属核验.json")
data = json.loads(VER.read_text(encoding="utf-8"))
targets = [(k, v) for k, v in data.items() if v.get("status") == "ok"]
print(f"已核实官网 {len(targets)} 家，开始体检\n")

rows = []
for name, meta in targets:
    site = meta["site"]
    try:
        r = H.audit(site)
    except Exception as e:
        print(f"  [ERR] {name}: {e}")
        continue
    rows.append({"name": name, **r})
    b = r["checks"]["robots"]["blocked"]
    print(f"  {r['score']:3d}分 [{r['grade']}] {name[:20]:22} "
          f"拦AI爬虫={b or '无'}")
    time.sleep(0.4)

(OUT / "results.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"\n=== 汇总（{len(rows)} 家）===")
avg = sum(r["score"] for r in rows) / len(rows) if rows else 0
print(f"平均分: {avg:.1f}")
for g in ("差", "中", "优"):
    n = sum(1 for r in rows if r["grade"] == g)
    print(f"  {g}: {n} 家")
blocked_n = sum(1 for r in rows if r["checks"]["robots"]["blocked"])
print(f"robots 拦截 AI 爬虫: {blocked_n} 家")
no_schema = sum(1 for r in rows if not r["checks"]["schema"]["exists"])
print(f"无结构化数据: {no_schema} 家")
no_llms = sum(1 for r in rows if not r["checks"]["llms"]["exists"])
print(f"无 llms.txt: {no_llms} 家")

# 最值得打的：分数低 + 拦 AI 爬虫（问题最痛）
hot = sorted(rows, key=lambda x: (x["score"], -len(x["checks"]["robots"]["blocked"])))
print("\n=== 优先敲门（问题最痛的前 10 家）===")
for r in hot[:10]:
    print(f"  {r['score']:3d}分 {r['name'][:22]:24} 拦={r['checks']['robots']['blocked']}")