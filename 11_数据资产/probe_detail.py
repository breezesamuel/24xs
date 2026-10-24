# -*- coding: utf-8 -*-
"""验证 ccgp 详情页字段抽取质量 —— 决定「一篇档案」能不能成立。"""
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


def get(u, tries=2):
    last = None
    for _ in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                       timeout=25, context=CTX)
            raw = r.read()
            for e in ("utf-8", "gbk", "gb18030"):
                try:
                    return raw.decode(e)
                except UnicodeDecodeError:
                    pass
            return raw.decode("utf-8", "ignore")
        except Exception as ex:
            last = ex
            time.sleep(1.5)
    raise last


def listurl(p, kw="医院"):
    q = urllib.parse.urlencode({
        "searchtype": 1, "page_index": p, "bidSort": 0, "buyerName": "",
        "projectId": "", "pinMu": 0, "bidType": 0, "dbselect": "bidx",
        "kw": kw, "start_time": "2025:01:01", "end_time": "2026:10:01",
        "timeType": 6, "displayZone": "", "zoneId": "", "pppStatus": 0,
        "agentName": "",
    })
    return "http://search.ccgp.gov.cn/bxsearch?" + q


def links(page):
    s = get(listurl(page))
    out = []
    for it in re.findall(r"<li[^>]*>(.*?)</li>", s, re.S):
        a = re.search(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", it, re.S)
        if a:
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", a.group(2))).strip()
            u = a.group(1)
            if u.startswith("./"):
                u = "http://www.ccgp.gov.cn" + u[1:]
            if len(t) >= 8 and "t" in u and ".htm" in u:
                out.append((t, u))
    return out


def flat(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)
    return re.sub(r"[ \t　]+", " ", re.sub(r"\s*\n\s*", " ", re.sub(r"<[^>]+>", " ", s)))


FIELDS = ["采购人", "采购人名称", "采购人地址", "代理机构", "代理机构名称",
          "采购项目编号", "项目编号", "预算金额", "最高限价", "开标时间",
          "采购需求", "公告发布时间", "所属地区"]

print("=== 详情页字段抽取质量 (3 篇样本) ===")
got = 0
for title, url in links(1)[:3]:
    print("\n--- %s" % title[:60])
    print("    %s" % url)
    try:
        txt = flat(get(url))
    except Exception as e:
        print("    取页失败: %s" % type(e).__name__)
        continue
    got += 1
    print("    正文 %d 字" % len(txt))
    for f in FIELDS:
        m = re.search(re.escape(f) + r"\s*[：:]\s*([^\n]{2,120})", txt)
        print("      %-12s %s" % (f, (m.group(1).strip()[:78] if m else "-")))
    time.sleep(1.2)

print("\n成功取到 %d/3 篇" % got)
