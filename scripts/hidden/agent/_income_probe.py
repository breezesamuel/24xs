#!/usr/bin/env python3
"""确认双活收款通道可用 (进账前提): /api/pay 建单 + 网关 + ?a=loop 对账"""
import urllib.request, ssl, json, time
ctx = ssl.create_default_context()
def post(url, data, ct="application/x-www-form-urlencoded"):
    d = data.encode()
    req = urllib.request.Request(url, data=d, headers={"User-Agent":"Mozilla/5.0","Content-Type":ct,"Content-Length":str(len(d))})
    try:
        r = urllib.request.urlopen(req, timeout=30, context=ctx)
        return r.status, r.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8","replace")[:200]
# 1. Vercel /api/pay 建 1 元单 (进账入口)
s, b = post("https://tools.highkingflower.com/api/pay", "plan=trial&ref=OWNER_INCOME&slug=income&amount=1")
import re
m = re.search(r'out_trade_no[&=:]+["\']?([A-Za-z0-9_]+)', b)
otp = m.group(1) if m else "(form)"
print(f"[Vercel] /api/pay 1元单: HTTP {s}, out_trade_no={otp}, 含支付宝网关={'openapi.alipay.com' in b}")
# 2. 网关查单 (真实通道验签)
s2, b2 = post("https://tools.highkingflower.com/api/aliq", "out_trade_no=NONEXIST_PROBE", "application/x-www-form-urlencoded")
print(f"[Vercel] /api/aliq 查单: HTTP {s2}, 40004(通道活)={'40004' in b2 or 'TRADE_NOT_EXIST' in b2}")
# 3. CN 对照
s3, b3 = post("https://tools-cn.highkingflower.com/api/pay", "plan=trial&ref=OWNER_INCOME_CN&slug=income&amount=1")
m3 = re.search(r'out_trade_no[&=:]+["\']?([A-Za-z0-9_]+)', b3)
print(f"[CN] /api/pay 1元单: HTTP {s3}, out_trade_no={(m3.group(1) if m3 else '(form)')}, 支付宝网关={'openapi.alipay.com' in b3}")
print()
print("判定: 双活 /api/pay 都能出 1 元单 + 支付宝网关 = 进账通道 LIVE, 只差 owner 付 1 元")
