# -*- coding: utf-8 -*-
"""清理真实名单 CSV 里的非法号码。

背景：数据库当时清理过（祺鑫、小码王），但 CSV 是源文件，没跟着改。
只要 CSV 还带着垃圾号，任何按 CSV 重新导入的流程都会把它写回去。
"""
from __future__ import annotations

import csv
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(r"F:\2026\24xs\01_引擎")))
sys.stdout.reconfigure(encoding="utf-8")

import phoneutil  # noqa: E402

LEAD_DIR = Path(r"F:\2026\24xs\99_产出\获客名单")
# 备份必须放到子目录。放在同目录的话，备份文件名同样匹配
# `真实名单_*.csv`，任何读这个 glob 的脚本都会把备份当成新名单读一遍，
# 凭空多出 9 条重复线索。
BACKUP_DIR = LEAD_DIR / "_backup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

changed_total = 0
for p in sorted(LEAD_DIR.glob("真实名单_*.csv")):
    if ".bak-" in p.name:
        continue
    with p.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
        fields = list(rows[0].keys()) if rows else []

    fixed = 0
    for r in rows:
        for col in ("电话", "微信", "邮箱"):
            v = (r.get(col) or "").strip()
            if not v or v == "-":
                continue
            if col == "电话" and not phoneutil.is_valid(v):
                norm = phoneutil.normalize(v)
                keep = norm if norm and phoneutil.is_valid(norm) else ""
                print(f"  [清] {r.get('公司')}  {col}: {v!r} -> {keep!r}")
                r[col] = keep
                fixed += 1
            elif col == "电话":
                r[col] = phoneutil.normalize(v) or v

    if fixed:
        bak = BACKUP_DIR / f"{p.stem}.bak-{stamp}.csv"
        shutil.copy2(p, bak)
        with p.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"  已重写 {p.name}  改动 {fixed} 处  备份 {bak.name}")
        changed_total += fixed

print()
print("=" * 70)
if changed_total:
    print(f"共清理 {changed_total} 处非法号码")
else:
    print("CSV 里没有非法号码")
print("=" * 70)
