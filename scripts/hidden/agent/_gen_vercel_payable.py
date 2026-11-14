#!/usr/bin/env python3
"""生成 Vercel 1 元可付订单 (赚钱回路 0->1 入口)"""
import urllib.request, ssl, re
ctx = ssl.create_default_context()
data = "plan=trial&ref=MONELOOP_1&slug=moneyloop&amount=1".encode()
req = urllib.request.Request("https://tools.highkingflower.com/api/pay", data=data,
    headers={"User-Agent":"Mozilla/5.0","Content-Type":"application/x-www-form-urlencoded","Content-Length":str(len(data))})
try:
    r = urllib.request.urlopen(req, timeout=30, context=ctx)
    html = r.read().decode("utf-8","replace")
    m = re.search(r'"out_trade_no"\s*:\s*"([^"]+)"', html)
    print("Vercel 1 元可付订单:", m.group(1) if m else "(form 无 out_trade_no 内联, 看 form action/隐藏域)")
    open("F:/2026/24xs/scripts/hidden/agent/_payable_moneyloop_Vercel.html","w",encoding="utf-8").write(html)
    print("  收银台 form 已存: _payable_moneyloop_Vercel.html (owner 打开付 1 元)")
except Exception as e:
    print("Vercel 建单失败:", type(e).__name__, str(e)[:80])
