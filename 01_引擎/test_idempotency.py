# -*- coding: utf-8 -*-
"""幂等性验收：连续跑 3 次 `cli.py all`，关键表行数必须不增长。

修复前：leads.company 无唯一约束，build_pool 每跑一次就把同一批公司
再插一遍；outreach 也无唯一约束，同一线索排多条相同触达。
修复后：唯一索引 + INSERT OR IGNORE，重复运行为 no-op。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402

SNAPSHOT = """
SELECT
  (SELECT COUNT(*) FROM leads)                                        AS leads,
  (SELECT COUNT(*) FROM leads WHERE TRIM(COALESCE(company,''))<>'')  AS leads_named,
  (SELECT COUNT(*) FROM outreach)                                     AS outreach,
  (SELECT COUNT(*) FROM geo_probes)                                   AS probes,
  (SELECT COUNT(*) FROM corpus)                                       AS corpus
"""


def snap() -> dict:
    r = db.q(SNAPSHOT)[0]
    return {k: r[k] for k in r.keys()}


def main() -> int:
    from cli import main as cli_main

    db.init()
    before = snap()
    print("baseline:", before)

    for i in (1, 2, 3):
        cli_main(["all"])
        s = snap()
        print(f"after run {i}: {s}")
        if i >= 2 and s != before:
            print(f"[FAIL] 第 {i} 次运行改变了计数，幂等性被破坏")
            for k in before:
                if before[k] != s[k]:
                    print(f"   {k}: {before[k]} -> {s[k]}")
            return 1

    # 同公司重复行
    dup = db.q("""SELECT company, COUNT(*) n FROM leads
                  WHERE TRIM(COALESCE(company,''))<>''
                  GROUP BY company HAVING n>1 LIMIT 5""")
    if dup:
        print(f"[FAIL] 仍有重复公司: {[d['company'] for d in dup]}")
        return 1

    # 同线索重复触达
    dupo = db.q("""SELECT lead_id, channel, template, COUNT(*) n FROM outreach
                   GROUP BY lead_id, channel, template HAVING n>1 LIMIT 5""")
    if dupo:
        print(f"[FAIL] 仍有重复触达: {[(d['lead_id'], d['channel']) for d in dupo]}")
        return 1

    print("[OK] 连续 3 次 `cli.py all` 计数稳定，无重复公司/触达")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
