# -*- coding: utf-8 -*-
"""关键判定：page_index 到底生效没有？
若各页返回内容一致 => 分页参数被忽略 => 该源无法规模化，必须换源。"""
import hashlib
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


def url(p, kw="医院"):
    q = urllib.parse.urlencode({
        "searchtype": 1, "page_index": p, "bidSort": 0, "buyerName": "",
        "projectId": "", "pinMu": 0, "bidType": 0, "dbselect": "bidx",
        "kw": kw, "start_time": "2025:01:01", "end_time": "2026:10:01",
        "timeType": 6, "displayZone": "", "zoneId": "", "pppStatus": 0,
        "agentName": "",
    })
    return "http://search.ccgp.gov.cn/bxsearch?" + q


def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                               timeout=25, context=CTX)
    return r.read().decode("utf-8", "ignore")


def titles(s):
    out = []
    for it in re.findall(r"<li[^>]*>(.*?)</li>", s, re.S):
        a = re.search(r"<a[^>]*href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", it, re.S)
        if a:
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", a.group(2))).strip()
            if len(t) >= 8:
                out.append(t)
    return out


print("=== page_index 生效性判定 ===")
sigs = {}
for p in [1, 2, 3, 4]:
    try:
        s = get(url(p))
    except Exception as e:
        print("  page %d ERR %s" % (p, type(e).__name__))
        time.sleep(1.5)
        continue
    ts = titles(s)
    body_sig = hashlib.md5(
        re.sub(r"\s+", " ", re.sub(r"[^一-鿿]", "", s)).strip().encode()
    ).hexdigest()[:12]
    sigs[p] = body_sig
    print("  page %-2d 标题数=%-3d 正文指纹=%s" % (p, len(ts), body_sig))
    if ts:
        print("        首条: %s" % ts[0][:56])
        print("        末条: %s" % ts[-1][:56])
    time.sleep(1.4)

uniq = len(set(sigs.values()))
print()
print("  不同正文指纹数: %d / %d 页" % (uniq, len(sigs)))
if uniq <= 1:
    print("  判定: 分页参数被忽略，每页返回同一批 -> 该源不能规模化")
else:
    print("  判定: 分页生效 -> 可规模化")

print()
print("=== 顺带确认 ccgp 是否有独立的日期归档（可绕过分页）===")
for u in ["http://www.ccgp.gov.cn/cggg/dfgg/gkzb/index.htm",
          "http://www.ccgp.gov.cn/cggg/dfgg/gkzb/",
          "http://www.ccgp.gov.cn/cggg/zygg/gkzb/index.htm"]:
    try:
        s = get(u)
        links = re.findall(r'href=[\"\']([^\"\']*t\d{8}_\d+\.htm)[\"\']', s)
        print("  %-52s %6dB 公告链接=%d" % (u[-52:], len(s), len(links)))
        if links:
            print("       样例: %s" % links[0])
    except Exception as e:
        print("  %-52s ERR %s" % (u[-52:], type(e).__name__))
    time.sleep(1.0)
