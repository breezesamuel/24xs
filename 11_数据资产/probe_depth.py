# -*- coding: utf-8 -*-
"""决定性测算：ccgp 单个关键词能翻多深 = 总量天花板。"""
import io
import json
import re
import sys
import time

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
import ccgp_pipeline as P  # noqa


def depth_probe(kw, pages, dbselect="bidx"):
    """返回 (最大有效页, 每页条目数, 最后页总条目估计)。"""
    last_ok = 0
    per_page = 0
    first_titles = []
    for p in pages:
        try:
            rows = P.parse_list(P._get(P.search_url(p, kw, dbselect)))
        except Exception as e:
            print("   %s p%-4d ERR %s" % (kw, p, type(e).__name__))
            time.sleep(2.0)
            continue
        good = [r for r in rows if ".htm" in r["url"]]
        if good:
            last_ok = p
            per_page = max(per_page, len(good))
            if p == 1:
                first_titles = [g["title"][:30] for g in good[:2]]
        else:
            print("   %s p%-4d 空 -> 停止" % (kw, p))
            break
        time.sleep(1.1)
    return last_ok, per_page, first_titles


PROBE = [10, 50, 100, 200, 300, 500, 800, 1200]
out = []
print("=== 翻页深度探测 ===")
for kw in ["医院", "学校", "软件", "电梯"]:
    last, per, t0 = depth_probe(kw, PROBE)
    est = last * per
    print("  %-6s 最大有效页=%-5d 每页≈%-3d 总量估计≈%s 条" % (kw, last, per, f"{est:,}"))
    out.append({"kw": kw, "max_page": last, "per_page": per, "est_total": est})

print()
print("=== 多公告类型（同一关键词）===")
for db, label in [("bidx", "公开招标"), ("yixb", "邀请招标"), ("jztp", "竞争性谈判"),
                  ("jzcs", "竞争性磋商"), ("xunjia", "询价"), ("dyly", "单一来源")]:
    last, per, _ = depth_probe("医院", [10, 100, 300, 600])
    print("  %-8s(%s) 最大页=%-4d 总量估计≈%s"
          % (label, db, last, f"{last*per:,}"))
    out.append({"db": db, "label": label, "max_page": last, "est_total": last * per})

with io.open(r"F:\2026\24xs\11_数据资产\_深度报告.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
