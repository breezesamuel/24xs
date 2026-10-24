# -*- coding: utf-8 -*-
"""
ICP 备案 -> 域名反查企业主体。
这是突破「采购人上限」的唯一已验证方向：一个域名 = 一家真实注册企业。
全国 ICP 备案主体数在百万量级。
先攻接口（beian.miit.gov.cn 首页 521，hlwicpfwc 根 200），找出可用查询通道。
"""
import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9",
    "Origin": "https://beian.miit.gov.cn",
    "Referer": "https://beian.miit.gov.cn/",
}
COOKIE = "uuid=probe; HMF_CI=probe"


def post(url, data=None, hdrs=None, timeout=25):
    h = dict(UA)
    if hdrs:
        h.update(hdrs)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        h["Content-Type"] = "application/json;charset=UTF-8"
    req = urllib.request.Request(url, data=body, headers=h, method="POST")
    r = urllib.request.urlopen(req, timeout=timeout, context=CTX)
    raw = r.read()
    try:
        return r.status, json.loads(raw.decode("utf-8", "ignore"))
    except Exception:
        return r.status, raw[:300].decode("utf-8", "ignore")


def get(url, timeout=25):
    h = dict(UA)
    h["Referer"] = "https://beian.miit.gov.cn/"
    r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout, context=CTX)
    return r.status, r.read()[:200000]


# 工信部 ICP 备案查询接口（公开查询入口）
API = "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/auth"
API2 = "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/icpAbbreviateInfo/queryByCondition"

print("=== 1. 取 auth token ===")
tok = None
for hdr in [{"sign": "", "uuid": "", "token": ""},
            {"sign": "0", "uuid": "x", "token": "x"}]:
    try:
        st, j = post(API, {}, {"sign": "", "uuid": "", "token": "", **hdr})
        print("  status", st, "resp", str(j)[:200])
        if isinstance(j, dict) and j.get("token"):
            tok = j["token"]
            break
    except urllib.error.HTTPError as e:
        print("  HTTP", e.code, e.reason)
    except Exception as e:
        print("  ERR", type(e).__name__, str(e)[:80])
    time.sleep(1.2)

if not tok:
    print("  未取到 token（该接口需 sign/uuid 校验，疑似需先过首页拿动态参数）")

print()
print("=== 2. 尝试 queryByCondition（用探针域名查）===")
for payload in [
    {"unitName": "qq.com", "serviceType": 1, "pageNo": 1, "pageSize": 10},
    {"unitName": "baidu.com", "serviceType": 1, "pageNo": 1, "pageSize": 10},
]:
    try:
        st, j = post(API2, payload, {"token": tok or ""})
        print("  %s -> %s %s" % (payload.get("unitName"), st, str(j)[:220]))
    except urllib.error.HTTPError as e:
        print("  %s -> HTTP %s" % (payload.get("unitName"), e.code))
    except Exception as e:
        print("  %s -> ERR %s %s" % (payload.get("unitName"), type(e).__name__, str(e)[:60]))
    time.sleep(1.2)

print()
print("=== 3. 首页/JS 资源（找 sign 生成逻辑与真实接口路径）===")
for u in ["https://beian.miit.gov.cn/",
          "https://hlwicpfwc.miit.gov.cn/icpproject_query/api/",
          "https://hlwicpfwc.miit.gov.cn/"]:
    try:
        st, b = get(u)
        print("  %-58s %s %dB" % (u[-58:], st, len(b)))
    except Exception as e:
        print("  %-58s ERR %s %s" % (u[-58:], type(e).__name__, str(e)[:50]))
    time.sleep(1.0)

print()
print("=== 4. 备选：第三方公开备案查询（仅探测可达性）===")
alt = [
    "https://icp.chinaz.com/",
    "https://beianx.cn/",
    "https://www.beianx.cn/search/baidu.com",
    "https://icp.aliyun.com/",
    "https://whois.chinaz.com/",
]
for u in alt:
    try:
        st, b = get(u, 20)
        print("  %-46s %s %dB" % (u[-46:], st, len(b)))
    except Exception as e:
        print("  %-46s ERR %s" % (u[-46:], type(e).__name__))
    time.sleep(1.2)
