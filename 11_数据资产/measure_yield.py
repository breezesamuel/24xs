# -*- coding: utf-8 -*-
"""
决定性测算：唯一采购人产出率。
ccgp 通知条数 != 企业篇数。必须实测「每 N 条公告能去重出多少家企业」。
这是决定 100 万篇能否达成的唯一可信数字。
"""
import io
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
import crawler24 as C  # noqa

YIELD_DB = os.path.join(C.BASE, "yield_test.db")
if os.path.exists(YIELD_DB):
    os.remove(YIELD_DB)
con = sqlite3.connect(YIELD_DB)
con.executescript("""
CREATE TABLE n(url TEXT PRIMARY KEY, buyer TEXT, province TEXT, publish_date TEXT,
               budget_cny REAL, channel TEXT, project_name TEXT, agency TEXT);
CREATE INDEX i_b ON n(buyer);
""")
con.commit()

BUDGET_SEC = float(sys.argv[1]) if len(sys.argv) > 1 else 1500.0
KW = sys.argv[2] if len(sys.argv) > 2 else "医院"

# 医院 2024-2026，按省切分（每查询上限 1000 条）
PLAN = [("医院", "bidx", y, z, n) for y in (2026, 2025, 2024)
        for z, n in [("110000", "北京"), ("310000", "上海"), ("440000", "广东"),
                     ("330000", "浙江"), ("370000", "山东")]]


def u(page, db, y, z):
    q = urllib.parse.urlencode({
        "searchtype": 1, "page_index": page, "bidSort": 0, "buyerName": "",
        "projectId": "", "pinMu": 0, "bidType": 0, "dbselect": db, "kw": KW,
        "start_time": "%d:01:01" % y, "end_time": "%d:12:31" % y,
        "timeType": 6, "displayZone": "", "zoneId": z, "pppStatus": 0,
        "agentName": "",
    })
    return "http://search.ccgp.gov.cn/bxsearch?" + q


t_end = time.time() + BUDGET_SEC
seen = set()
got = kept = 0
empty_streak = 0

print("=== 唯一采购人产出率实测（预算 %.0f 秒）===" % BUDGET_SEC)
for _kw, db, y, z, pname in PLAN:
    if time.time() > t_end:
        break
    for p in range(1, 51):
        if time.time() > t_end:
            break
        try:
            items = C.parse_list(C.get(u(p, db, y, z), tries=2))
        except Exception:
            break
        if not items:
            empty_streak += 1
            break
        empty_streak = 0
        for title, url in items:
            if url in seen:
                continue
            if time.time() > t_end:
                break
            try:
                d = C.parse_detail(C.get(url, tries=2), url)
            except Exception:
                continue
            seen.add(url)
            got += 1
            if d.get("buyer"):
                kept += 1
                con.execute("INSERT OR IGNORE INTO n VALUES (?,?,?,?,?,?,?,?)",
                            (url, d["buyer"], pname, d.get("publish_date", ""),
                             d.get("budget_cny", 0.0), d.get("channel", ""),
                             d.get("project_name", ""), d.get("agency", "")))
                con.commit()
            time.sleep(0.30)
        time.sleep(1.3)
    n = con.execute("SELECT COUNT(*) FROM n").fetchone()[0]
    uq = con.execute("SELECT COUNT(DISTINCT buyer) FROM n").fetchone()[0]
    print("  %d/%s 抓取=%-4d 入库=%-4d 唯一采购人=%-4d" % (y, pname, got, kept, uq))

n = con.execute("SELECT COUNT(*) FROM n").fetchone()[0]
uq = con.execute("SELECT COUNT(DISTINCT buyer) FROM n").fetchone()[0]
withbud = con.execute("SELECT COUNT(*) FROM n WHERE budget_cny>0").fetchone()[0]
provs = con.execute("SELECT COUNT(DISTINCT province) FROM n").fetchone()[0]
top = list(con.execute("SELECT buyer,COUNT(*) c FROM n GROUP BY buyer "
                       "ORDER BY c DESC LIMIT 12"))

ratio = uq / n if n else 0
rep = {
    "关键词": KW, "抓取条数": got, "入库条数": n, "唯一采购人": uq,
    "唯一率": round(ratio, 4), "去重比": ("1条公告对应 %.2f 个采购人" % (1 / ratio)) if ratio else "",
    "有金额条数": withbud, "覆盖省份": provs,
    "单线程秒每条": round((time.time() - (t_end - BUDGET_SEC)) / max(got, 1), 2),
    "前12采购人": [{"name": a, "n": b} for a, b in top],
}
with io.open(os.path.join(C.BASE, "_产出率报告.json"), "w", encoding="utf-8") as f:
    json.dump(rep, f, ensure_ascii=False, indent=2)
print("\n抓取 %d -> 入库 %d -> 唯一采购人 %d（唯一率 %.1f%%）" % (got, n, uq, ratio * 100))
con.close()
print("写入 _产出率报告.json")
