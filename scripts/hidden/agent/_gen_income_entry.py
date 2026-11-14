#!/usr/bin/env python3
"""生成 owner 可点的 1 元进账入口 (双活 Alipay 收银台 form) -> 付 1 元 = 真实进账 0->1"""
import urllib.request, ssl, re
ctx = ssl.create_default_context()
def make(base, ref, slug):
    data = f"plan=trial&ref={ref}&slug={slug}&amount=1".encode()
    req = urllib.request.Request(base + "/api/pay", data=data,
        headers={"User-Agent":"Mozilla/5.0","Content-Type":"application/x-www-form-urlencoded","Content-Length":str(len(data))})
    r = urllib.request.urlopen(req, timeout=30, context=ctx)
    html = r.read().decode("utf-8","replace")
    m = re.search(r'(out_trade_no)[^A-Za-z0-9_]*([A-Za-z0-9_]+)', html.replace("&quot;",""))
    otp = m.group(2) if m else "(见form)"
    fname = f"F:/2026/24xs/scripts/hidden/agent/_payable_{ref}.html"
    open(fname, "w", encoding="utf-8").write(html)
    print(f"  {base:40s} out_trade_no={otp:40s} -> {fname.split('/')[-1]}")
print("=== 生成 1 元进账入口 (owner 打开付 1 元 = 真实进账 0->1) ===")
make("https://tools.highkingflower.com", "OWNER_INCOME", "income")     # Vercel
make("https://tools-cn.highkingflower.com", "OWNER_INCOME_CN", "income")  # CN
print()
print("操作: owner 双击上述 .html -> 自动提交到支付宝 -> 付 1 元 -> 回跳 /paid + 服务端 /api/notify 自动开通+记返现+对账")
print("验证进账: /api/order?out_trade_no=<上面单号> 看 trade_status=SUCCESS; /api/autoops.js?a=loop 看 revenue>0")
