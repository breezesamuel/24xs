#!/usr/bin/env python3
"""生成 1 元可付订单 (Vercel+CN), 供 owner 付 1 元让 "真实收款 0->1"。
读 /api/pay 建单, 抓收银台 form, 存 HTML。"""
import urllib.request, ssl, re, time
ctx = ssl.create_default_context()
def pay(base, ref):
    data = f"plan=trial&ref={ref}&slug=moneyloop&amount=1".encode()
    req = urllib.request.Request(base+"/api/pay", data=data,
        headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0)","Content-Type":"application/x-www-form-urlencoded","Content-Length":str(len(data)),"Connection":"close"})
    try:
        r = urllib.request.urlopen(req, timeout=30, context=ctx)
        html = r.read().decode("utf-8","replace")
        m = re.search(r'"out_trade_no"\s*:\s*"([^"]+)"', html)
        otp = m.group(1) if m else "(未抓到)"
        return otp, html
    except Exception as e:
        return "(ERR: %s)" % str(e)[:60], ""
# CN (Vercel 部署 down, 先出 CN)
otp, html = pay("https://tools-cn.highkingflower.com", "MONELOOP_1")
print("CN 1 元可付订单 out_trade_no:", otp)
if html:
    open("F:/2026/24xs/scripts/hidden/agent/_payable_moneyloop_CN.html","w",encoding="utf-8").write(html)
    print("  收银台 form 已存: scripts/hidden/agent/_payable_moneyloop_CN.html")
print("(Vercel 部署 down, 待网络恢复再出 Vercel 可付订单)")
