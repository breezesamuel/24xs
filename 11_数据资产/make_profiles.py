# -*- coding: utf-8 -*-
"""
企业档案 -> 可售资产生成器

对库里每家真实采购人，生成一份可交付的企业档案卡（HTML+JSON+CSV）。
这是「数字资产」的产品形态：不是原始公告堆砌，而是可验证、可交付的结构化档案。

只含公开公告字段。不含任何个人信息。
"""
import csv
import io
import json
import os
import re
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, r"F:\2026\24xs\11_数据资产")
import crawler24 as C  # noqa

DB = os.path.join(C.BASE, "ccgp_production.db")
OUT = os.path.join(C.BASE, "assets")
os.makedirs(OUT, exist_ok=True)


def slug(name):
    s = re.sub(r"[^\w一-鿿]+", "_", name).strip("_")
    return (s[:40] or "x")


def load():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = c.execute("""SELECT buyer,
        COUNT(*) n, SUM(budget_cny) budget, MAX(publish_date) latest,
        GROUP_CONCAT(DISTINCT province) provs, GROUP_CONCAT(DISTINCT channel) chans,
        GROUP_CONCAT(DISTINCT agency) agens, MAX(buyer_address) addr
        FROM notices WHERE buyer<>'' GROUP BY buyer""").fetchall()
    c.close()
    return rows


def one_company(r):
    d = dict(r)
    n = d["n"] or 1
    provs = [p for p in (d["provs"] or "").split(",") if p]
    chans = [p for p in (d["chans"] or "").split(",") if p]
    agens = [p for p in (d["agens"] or "").split(",") if p if p]
    avg = (d["budget"] or 0) / n
    return {
        "name": d["buyer"],
        "公告数": n,
        "累计预算_元": round(d["budget"] or 0, 2),
        "单笔均预算_元": round(avg, 2),
        "最近公告": d["latest"] or "",
        "涉及省份": provs,
        "公告类型": chans,
        "常见代理机构": agens[:5],
        "地址": d["addr"] or "",
    }


HTML = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} · 采购档案</title>
<meta name="description" content="{name}政府采购公开公告档案：{n}条公告，累计预算{budget}元，最近公告{latest}。数据来源：中国政府采购网公开公告。">
<style>body{{font:15px/1.7 -apple-system,"PingFang SC",sans-serif;max-width:720px;margin:0 auto;padding:32px 20px;color:#1f2328}}
h1{{font-size:22px;margin:0 0 4px}}.s{{color:#59636e;font-size:13px}}
table{{width:100%;border-collapse:collapse;margin:16px 0;font-size:14px}}
th,td{{text-align:left;padding:8px;border-bottom:1px solid #d0d7de}}
th{{color:#59636e;font-size:12px}}.k{{width:120px;color:#59636e}}
.b{{background:#f6f8fa;padding:12px 16px;border-left:3px solid #1f6feb;border-radius:0 8px 8px 0}}
.n{{display:inline-block;background:#1f6feb;color:#fff;border-radius:6px;padding:2px 8px;font-size:12px;margin-right:6px}}
footer{{margin-top:32px;padding-top:16px;border-top:1px solid #d0d7de;color:#59636e;font-size:12px}}
</style></head><body>
<h1>{name}</h1>
<div class="s">政府采购公开公告档案 · 数据源：中国政府采购网</div>
<div class="b" style="margin-top:16px">
共 <b>{n}</b> 条公开采购公告，累计预算 <b>{budget}</b> 元，单笔均 <b>{avg}</b> 元。
最近一次公告：<b>{latest}</b>。
</div>
<h2 style="font-size:17px;margin-top:26px">基础信息</h2>
<table>
<tr><td class="k">主体名称</td><td>{name}</td></tr>
<tr><td class="k">涉及省份</td><td>{provs}</td></tr>
<tr><td class="k">公告类型</td><td>{chans}</td></tr>
<tr><td class="k">常见代理机构</td><td>{agens}</td></tr>
<tr><td class="k">公开地址</td><td>{addr}</td></tr>
</table>
<h2 style="font-size:17px;margin-top:26px">采购活跃度解读</h2>
<p>{read}</p>
<footer>
本档案由丙大山数据资产基于公开政府采购公告自动生成，可复现、可复核。
仅含公开信息，不含任何个人信息。<br>
<a href="../../index.html">返回资产总览</a>
</footer>
</body></html>
"""


def read_text(d):
    n = d["公告数"]
    avg = d["单笔均预算_元"]
    t = []
    if n >= 20:
        t.append("该主体采购非常活跃（%d 条公告），属高频采购单位。" % n)
    elif n >= 5:
        t.append("该主体采购较为活跃（%d 条公告）。" % n)
    else:
        t.append("该主体公开采购记录较少（%d 条）。" % n)
    if avg >= 5_000_000:
        t.append("单笔均预算 %.0f 万元，属大额采购，常走公开招标。" % (avg / 1e4))
    elif avg >= 500_000:
        t.append("单笔均预算 %.0f 万元，规模中等。" % (avg / 1e4))
    else:
        t.append("单笔均预算 %.0f 万元，以小额采购为主。" % (avg / 1e4))
    if "公开招标" in d["公告类型"]:
        t.append("有公开招标记录，通常要求供应商具备相应资质并已在政府采购网注册。")
    if d["常见代理机构"]:
        t.append("常用代理机构：%s。" % "、".join(d["常见代理机构"][:3]))
    return "".join(t)


def main():
    rows = load()
    made = 0
    csv_path = os.path.join(OUT, "企业档案总表.csv")
    allj = []
    for r in rows:
        d = one_company(r)
        s = slug(d["name"])
        allj.append(d)
        html = HTML.format(
            name=d["name"], n=d["公告数"],
            budget="{:,.0f}".format(d["累计预算_元"]),
            avg="{:,.0f}".format(d["单笔均预算_元"]),
            latest=d["最近公告"] or "-",
            provs="、".join(d["涉及省份"]) or "-",
            chans="、".join(d["公告类型"]) or "-",
            agens="、".join(d["常见代理机构"]) or "-",
            addr=d["地址"] or "-",
            read=read_text(d),
        )
        with io.open(os.path.join(OUT, s + ".html"), "w", encoding="utf-8") as f:
            f.write(html)
        made += 1

    with io.open(os.path.join(OUT, "企业档案总表.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["主体名称", "公告数", "累计预算(元)", "单笔均预算(元)",
                    "最近公告", "涉及省份", "公告类型", "地址"])
        for d in allj:
            w.writerow([d["name"], d["公告数"], d["累计预算_元"],
                        d["单笔均预算_元"], d["最近公告"],
                        "|".join(d["涉及省份"]), "|".join(d["公告类型"]), d["地址"]])
    with io.open(os.path.join(OUT, "企业档案.json"), "w", encoding="utf-8") as f:
        json.dump(allj, f, ensure_ascii=False, indent=2)
    print("生成档案页 %d 份" % made)
    print("总表: %s" % csv_path)


if __name__ == "__main__":
    main()
