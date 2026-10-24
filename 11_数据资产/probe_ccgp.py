# -*- coding: utf-8 -*-
"""验证唯一确认可达的分页批量源：中国政府采购网搜索。
目的：确认能否程序化翻页 + 提取结构化字段。这是能否产出量的关键。"""
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "http://www.ccgp.gov.cn/",
}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    r = urllib.request.urlopen(req, timeout=25, context=CTX)
    raw = r.read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return r.status, raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return r.status, raw.decode("utf-8", "ignore")


print("=== 中国政府采购网 分页能力验证 ===")
base = "http://search.ccgp.gov.cn/bxsearch"
ok_pages = 0
total_items = 0
sample = []

for page in (1, 2, 3, 5, 10):
    q = urllib.parse.urlencode({
        "searchtype": 1,
        "page_index": page,
        "bidSort": 0,
        "buyerName": "",
        "projectId": "",
        "pinMu": 0,
        "bidType": 0,
        "dbselect": "bidx",
        "kw": "医院",
        "start_time": "2025:01:01",
        "end_time": "2026:10:01",
        "timeType": 6,
        "displayZone": "北京",
        "zoneId": "110000",
        "pppStatus": 0,
        "agentName": "",
    })
    url = base + "?" + q
    try:
        status, html = fetch(url)
    except Exception as e:
        print("  page %-3d ERR %s" % (page, type(e).__name__))
        time.sleep(1.5)
        continue
    # 结果条目：<li ...>...<a href='...'>标题</a>
    items = re.findall(r"<li[^>]*>(.*?)</li>", html, re.S)
    good = []
    for it in items:
        a = re.search(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", it, re.S)
        if not a:
            continue
        title = re.sub(r"<[^>]+>", "", a.group(2))
        title = re.sub(r"\s+", " ", title).strip()
        if len(title) < 8:
            continue
        meta = re.sub(r"<[^>]+>", " ", it)
        meta = re.sub(r"\s+", " ", meta).strip()
        good.append((title[:70], a.group(1)[:90], meta[:150]))
    total_items += len(good)
    if good:
        ok_pages += 1
    print("  page %-3d http=%s html=%dB 解析到条目=%d" % (page, status, len(html), len(good)))
    if page == 1 and good:
        sample = good[:3]
    time.sleep(1.2)

print()
print("可达页数: %d / 5    单页条目样本合计: %d" % (ok_pages, total_items))
print()
print("=== 第 1 页前 3 条样本（判断字段可用性）===")
for t, u, m in sample:
    print("  标题: %s" % t)
    print("  链接: %s" % u)
    print("  上下文: %s" % m)
    print()

if ok_pages >= 2:
    print("结论: 可分页 -> 具备产出量的基础")
else:
    print("结论: 不可分页 -> 该源无法用于规模化生产")
