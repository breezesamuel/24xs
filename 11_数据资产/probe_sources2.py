# -*- coding: utf-8 -*-
"""探测公共数据开放平台 / 行业监管公开库 —— 找能批量出企业记录的合法源。"""
import concurrent.futures as cf
import ssl
import time
import urllib.error
import urllib.request

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

T = [
    ("国家公共数据开放平台", "https://data.gov.cn/"),
    ("上海市公共数据开放", "https://data.sh.gov.cn/"),
    ("北京市公共数据开放", "https://data.beijing.gov.cn/"),
    ("广东省公共数据开放", "https://data.gd.gov.cn/"),
    ("浙江省公共数据开放", "https://data.zj.gov.cn/"),
    ("江苏省公共数据开放", "http://data.jiangsu.gov.cn/"),
    ("山东省公共数据开放", "http://data.sd.gov.cn/"),
    ("四川省公共数据开放", "https://data.sc.gov.cn/"),
    ("湖北省公共数据开放", "http://data.hubei.gov.cn/"),
    ("河南省公共数据开放", "https://data.henan.gov.cn/"),
    ("安徽省公共数据开放", "https://data.ah.gov.cn/"),
    ("湖南省公共数据开放", "https://data.hunan.gov.cn/"),
    ("福建省公共数据开放", "https://data.fujian.gov.cn/"),
    ("ICP备案-工信部", "https://beian.miit.gov.cn/"),
    ("ICP备案查询API", "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/auth"),
    ("顺企网-公司列表", "https://www.11467.com/company/"),
    ("全国建筑业企业查询", "https://jzsc.mohurd.gov.cn/data/company/list"),
    ("水利部市场监管", "https://slj.mwr.gov.cn/"),
    ("知识产权局商标", "https://sbj.cnipa.gov.cn/"),
    ("药监局", "http://www.nmpa.gov.cn/"),
    ("全国医疗机构查询", "http://zgcx.nhc.gov.cn:9090/Unit"),
    ("民航局企业", "http://www.caac.gov.cn/"),
    ("金融监管总局", "https://www.cbirc.gov.cn/"),
    ("全国征信机构公示", "https://www.pbccrc.org.cn/"),
    ("上海市市场监管-许可", "https://scjgj.sh.gov.cn/"),
    ("全国公共信用信息平台", "http://www.creditchina.gov.cn/"),
    ("中国政府采购网搜索", "http://search.ccgp.gov.cn/bxsearch?searchtype=1&page_index=1"),
    ("招标投标公共服务平台", "https://bulletin.cebpubservice.com/xxfbcmses/search/bulletin.html"),
    ("全国12315平台", "https://www.12315.cn/"),
    ("中国海关企业进出口", "http://credit.customs.gov.cn/"),
]


def probe(item):
    name, url = item
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers=UA)
        r = urllib.request.urlopen(req, timeout=18, context=CTX)
        body = r.read(300000)
        head = body[:2500].decode("utf-8", "ignore")
        low = head.lower()
        if head.lstrip()[:1] in "[{":
            kind = "JSON"
        elif "<html" in low or "<!doctype" in low:
            kind = "HTML"
        else:
            kind = "OTHER"
        anti = []
        for token, tag in (("captcha", "验证码"), ("aliyun_waf", "WAF"),
                           ("just a moment", "CF挑战"), ("安全验证", "验证"),
                           ("access denied", "拒绝"), ("请输入验证码", "验证码"),
                           ("nginx", "nginx")):
            if token in low:
                anti.append(tag)
        return (name, url, r.status, len(body), kind, ",".join(anti) or "-",
                round(time.time() - t0, 1), "")
    except urllib.error.HTTPError as e:
        return (name, url, e.code, 0, "-", "-", round(time.time() - t0, 1),
                str(e.reason)[:45])
    except Exception as e:
        return (name, url, -1, 0, "-", "-", round(time.time() - t0, 1),
                type(e).__name__ + ":" + str(e)[:45])


with cf.ThreadPoolExecutor(max_workers=12) as ex:
    res = list(ex.map(probe, T))

ok = [r for r in res if r[2] == 200 and r[3] > 3000]
bad = [r for r in res if r not in ok]

print("=== 可达 (%d) ===" % len(ok))
for n, u, c, sz, k, a, t, e in sorted(ok, key=lambda x: -x[3]):
    print("  %-22s %-6s %8dB  %-5s anti=%-14s %ss" % (n, c, sz, k, a, t))
    print("       %s" % u)
print()
print("=== 不可达 (%d) ===" % len(bad))
for n, u, c, sz, k, a, t, e in bad:
    print("  %-22s %-5s %ss  %s" % (n, c, t, e))
    print("       %s" % u)
