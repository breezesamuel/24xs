# -*- coding: utf-8 -*-
"""排查：page50 为 0 条，到底是参数问题还是限流/封禁。"""
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


def raw(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                   timeout=25, context=CTX)
        b = r.read()
        return r.status, len(b), b
    except Exception as e:
        return -1, 0, type(e).__name__ + ": " + str(e)[:60]


def params(p, zone="", dz=""):
    q = urllib.parse.urlencode({
        "searchtype": 1, "page_index": p, "bidSort": 0, "buyerName": "",
        "projectId": "", "pinMu": 0, "bidType": 0, "dbselect": "bidx",
        "kw": "医院", "start_time": "2024:01:01", "end_time": "2026:10:01",
        "timeType": 6, "displayZone": dz, "zoneId": zone, "pppStatus": 0,
        "agentName": "",
    })
    return "http://search.ccgp.gov.cn/bxsearch?" + q


print("=== 逐步排查 ===")
for label, url in [
    ("zone=110000 page1 (上一版成功参数)", params(1, "110000", "北京")),
    ("zone='' page1", params(1)),
    ("zone='' page2", params(2)),
    ("zone='' page20", params(20)),
    ("zone='' page50", params(50)),
]:
    st, ln, body = raw(url)
    if st == 200 and isinstance(body, bytes):
        s = body.decode("utf-8", "ignore")
        items = re.findall(r"<li[^>]*>(.*?)</li>", s, re.S)
        good = [i for i in items if re.search(r"<a[^>]*href", i)]
        # 是否返回"没有找到"
        nomatch = "没有查询到" in s or "未查询到" in s or "共0条" in s or "暂无" in s
        print("  %-34s http=%s %6dB li=%-3d 有链接=%-3d 空结果提示=%s"
              % (label, st, ln, len(items), len(good), nomatch))
    else:
        print("  %-34s %s" % (label, body))
    time.sleep(1.5)

print()
print("=== 换关键词试深度（不同结果集深度可能不同）===")
for kw in ["医院", "学校", "软件", "电梯", "物业"]:
    for p in [1, 10, 30, 60]:
        q = urllib.parse.urlencode({
            "searchtype": 1, "page_index": p, "bidSort": 0, "buyerName": "",
            "projectId": "", "pinMu": 0, "bidType": 0, "dbselect": "bidx",
            "kw": kw, "start_time": "2020:01:01", "end_time": "2026:10:01",
            "timeType": 6, "displayZone": "", "zoneId": "", "pppStatus": 0,
            "agentName": "",
        })
        st, ln, body = raw("http://search.ccgp.gov.cn/bxsearch?" + q)
        n = 0
        if st == 200 and isinstance(body, bytes):
            s = body.decode("utf-8", "ignore")
            n = len([i for i in re.findall(r"<li[^>]*>(.*?)</li>", s, re.S)
                     if re.search(r"<a[^>]*href", i)])
        print("  kw=%-5s page=%-3d http=%s 条目=%d" % (kw, p, st, n))
        time.sleep(1.2)
        if n == 0:
            break
    print()
