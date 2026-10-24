# -*- coding: utf-8 -*-
"""确认 new_verified 名单与自动发送队列完全隔离，并清理验收用测试数据。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "01_引擎"))
import db  # noqa: E402

TEST = ("上海家装设计工程有限公司", "杭州装修公司")

nv = db.q("SELECT COUNT(*) n FROM leads WHERE status='new_verified'")[0]["n"]
leaked = db.q("""SELECT COUNT(*) n FROM outreach o
                 JOIN leads l ON l.id = o.lead_id
                 WHERE l.status='new_verified'""")[0]["n"]
print(f"new_verified 家数: {nv}")
print(f"其中已进入 outreach 队列的: {leaked}")

if leaked:
    print("[FAIL] 已核验名单泄漏进自动发送队列")
    raise SystemExit(1)

# 清掉验收用的假数据，保留真实导入的能力
with db.conn() as c:
    for name in TEST:
        c.execute("DELETE FROM leads WHERE company=?", (name,))
print(f"[OK] 已清理 {len(TEST)} 条验收测试数据")
print("[OK] 已核验名单与自动发送队列隔离正常")
