# -*- coding: utf-8 -*-
"""
决定性测试：ccgp 搜索每查询约 1000 条封顶。
若按年份/省份切分时间窗可重置配额 => 总量可放大 10 倍以上。
"""
import io
import json
import re
import sys
import time
import urllib.parse

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
import ccgp_pipeline as P  # noqa

PAGE_CAP_PROBE = [10, 40, 49, 50, 51, 60, 80]


def url_t(p, kw, st, et, dbselect="bidx", zone=""):
    q = urllib.parse.urlencode({
        "searchtype": 1, "page_index": p, "bidSort": 0, "buyerName": "",
        "projectId": "", "pinMu": 0, "bidType": 0, "dbselect": dbselect,
        "kw": kw, "start_time": st, "end_time": et,
        "timeType": 6, "displayZone": "", "zoneId": zone, "pppStatus": 0,
        "agentName": "",
    })
    return "http://search.ccgp.gov.cn/bxsearch?" + q


def probe(kw, st, et, dbselect="bidx", zone=""):
    last_ok = 0
    per = 0
    for p in PAGE_CAP_PROBE:
        try:
            rows = P.parse_list(P._get(url_t(p, kw, st, et, dbselect, zone)))
        except Exception:
            time.sleep(1.6)
            continue
        good = [r for r in rows if ".htm" in r["url"]]
        if good:
            last_ok = p
            per = max(per, len(good))
        else:
            break
        time.sleep(1.0)
    return last_ok, per


out = []
print("=== A. 精确封顶位置（医院 / 全时段）===")
last, per = probe("医院", "2010:01:01", "2026:10:01")
print("  最大有效页=%d 每页=%d -> 约 %d 条" % (last, per, last * per))
out.append({"case": "医院_全时段", "max_page": last, "per": per, "est": last * per})

print()
print("=== B. 按年份切分（关键：配额能否重置）===")
tot = 0
for y in range(2015, 2027):
    st = "%d:01:01" % y
    et = "%d:12:31" % y
    last, per = probe("医院", st, et)
    est = last * per
    tot += est
    print("  %d 年  最大页=%-4d 每页=%-3d 约 %6d 条" % (y, last, per, est))
    out.append({"case": "医院_%d年" % y, "max_page": last, "est": est})
print("  ---- 医院单关键词按年累加 = %d 条" % tot)
out.append({"case": "医院_按年合计", "est": tot})

print()
print("=== C. 年份 + 公告类型 交叉 ===")
tot2 = 0
for y in (2022, 2023, 2024, 2025):
    for db in ("bidx", "jztp", "jzcs", "xunjia", "dyly", "yixb"):
        last, per = probe("医院", "%d:01:01" % y, "%d:12:31" % y, db)
        est = last * per
        tot2 += est
        print("  %d %-7s 最大页=%-4d 约 %5d 条" % (y, db, last, est))
        time.sleep(0.5)
print("  ---- 4年 x 6类型 = %d 条（仅关键词=医院）" % tot2)
out.append({"case": "医院_年x类型", "est": tot2})

with io.open(r"F:\2026\24xs\11_数据资产\_配额报告.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("\n已写入 _配额报告.json")
