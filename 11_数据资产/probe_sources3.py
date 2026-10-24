# -*- coding: utf-8 -*-
"""
第二批源探测（礼貌限速）。目标是找「每个查询能翻很多页」的源，
因为单源每查询封顶 1000 条的话，100 万篇需要几百个查询组合。
"""
import io
import json
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
    "Accept-Language": "zh-CN,zh;q=0.9",
}

# (名称, 列表页URL模板, 公告链接正则)
SOURCES = [
    ("全国公共资源交易-工程建设", "https://www.ggzy.gov.cn/information/html/a/0000000000000000.html",
     r"t\d{8}_\d+\.htm|/a/\d{6,}\.html"),
    ("浙江省公共资源交易", "https://ggzy.zj.gov.cn/notice.html",
     r"noticeId=|\.html"),
    ("广东省公共资源交易", "https://ygp.gdzwfw.gov.cn/#/44/index",
     r"\.html"),
    ("江苏公共资源交易", "https://jsggzy.jszwfw.gov.cn/inteligentsearch/rest/inteligentSearch/getFullTextDataNew",
     r"\.json"),
    ("山东省公共资源交易中心", "http://ggzyjy.shandong.gov.cn/information/html/a/0000000000000000.html",
     r"t\d{8}_\d+\.htm"),
    ("中国招标投标公共服务平台", "https://bulletin.cebpubservice.com/xxfbcmses/search/bulletinlist.html",
     r"bulletinId=|\d{6,}\.html"),
    ("中国政府采购网-中标结果", "http://search.ccgp.gov.cn/bxsearch?searchtype=2&page_index=1&dbselect=zbj&kw=%E5%8C%BB%E9%99%A2",
     r"t\d{8}_\d+\.htm"),
    ("顺企网-上海公司", "https://www.11467.com/shanghai/dir1.htm",
     r"company\d+\.htm|/[a-z0-9]+/"),
    ("阿里巴巴供应商", "https://www.1688.com/",
     r"offerId"),
    ("猪八戒网服务市场", "https://zbj.com/xhr/search",
     r"/service/"),
]

# 只做「能不能拿到列表 + 列表里有没有可翻页的链接」判断，不暴力翻页
results = []
for name, url, linkre in SOURCES:
    t0 = time.time()
    rec = {"name": name, "url": url}
    try:
        req = urllib.request.Request(url, headers=UA)
        r = urllib.request.urlopen(req, timeout=25, context=CTX)
        body = r.read(400000)
        s = body.decode("utf-8", "ignore")
        if "�" in s[:2000] and s.encode("utf-8", "ignore").count(b"\xef\xbf\xbd") > 20:
            for e in ("gbk", "gb18030"):
                try:
                    s2 = body.decode(e)
                    if s2.count("�") < s.count("�"):
                        s = s2
                    break
                except Exception:
                    pass
        links = re.findall(linkre, s)
        rec.update({
            "http": r.status,
            "bytes": len(body),
            "links_found": len(links),
            "is_json": s.lstrip()[:1] in "[{",
            "need_js": bool(re.search(r"(?i)请开启|enable javascript|<noscript", s[:6000])),
            "anti": [t for t in ("验证码", "安全验证", "访问频繁", "稍后")
                     if t in s[:8000]],
            "sec": round(time.time() - t0, 1),
        })
    except Exception as e:
        rec.update({"http": -1, "bytes": 0, "links_found": 0,
                    "error": type(e).__name__ + ": " + str(e)[:50]})
    results.append(rec)
    print("%-26s %s" % (name, json.dumps(rec, ensure_ascii=False)[:190]))
    time.sleep(2.2)

with io.open(r"F:\2026\24xs\11_数据资产\_第二批源.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("\n写入 _第二批源.json")
