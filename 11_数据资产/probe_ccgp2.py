# -*- coding: utf-8 -*-
"""测 ccgp 分页深度上限 + 抽结构化字段（采购人=真实企业实体）。"""
import re
import ssl
import time
import urllib.parse
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.8,*/*;q=0.8",
    "Referer": "http://www.ccgp.gov.cn/",
}
BASE = "http://search.ccgp.gov.cn/bxsearch"


def page_url(p, kw="医院", zone="110000"):
    q = urllib.parse.urlencode({
        "searchtype": 1, "page_index": p, "bidSort": 0, "buyerName": "",
        "projectId": "", "pinMu": 0, "bidType": 0, "dbselect": "bidx",
        "kw": kw, "start_time": "2024:01:01", "end_time": "2026:10:01",
        "timeType": 6, "displayZone": "", "zoneId": zone, "pppStatus": 0,
        "agentName": "",
    })
    return BASE + "?" + q


def get(url):
    r = urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                               timeout=25, context=CTX)
    raw = r.read()
    for e in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(e)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "ignore")


def parse(html):
    out = []
    for it in re.findall(r"<li[^>]*>(.*?)</li>", html, re.S):
        a = re.search(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", it, re.S)
        if not a:
            continue
        t = re.sub(r"<[^>]+>", "", a.group(2))
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) < 8:
            continue
        meta = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", it)).strip()
        out.append((t, a.group(1), meta))
    return out


print("=== 分页深度探测（关键词:医院 / 北京）===")
depth_ok = 0
for p in [50, 100, 150, 200, 250, 300, 400]:
    try:
        items = parse(get(page_url(p)))
    except Exception as e:
        print("  page %-4d ERR %s" % (p, type(e).__name__))
        break
    same = items[0][0] if items else ""
    print("  page %-4d 条目=%-3d 首条=%s" % (p, len(items), same[:38]))
    if items:
        depth_ok = p
    time.sleep(1.0)
    if p >= 200 and not items:
        break

print("  -> 已验证可达最大页: %d  (x20条/页 = %d 条)" % (depth_ok, depth_ok * 20))

print()
print("=== 结构化字段抽取（采购人 = 真实企业实体）===")
url = page_url(1)
items = parse(get(url))
full = ""
for t, u, meta in items[:3]:
    try:
        full = get(u)
        break
    except Exception as e:
        print("  详情页失败 %s" % type(e).__name__)
if full:
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", full))
    print("  详情页长度: %d" % len(flat))
    for field in ["采购人", "采购人名称", "采购人地址", "代理机构", "项目编号",
                  "预算金额", "采购需求", "开标时间"]:
        m = re.search(field + r"[：:]\s*([^ ]{2,80})", flat)
        print("   %-8s -> %s" % (field, m.group(1)[:70] if m else "(未解析出)"))
else:
    print("  未能取到详情页")
