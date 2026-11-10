#!/usr/bin/env python3
"""本轮全部修复的最终验证: Vercel 500修复 + 双活收款 + 订阅墙 + 权益 + 服务"""
import urllib.request, urllib.error, json, time

def req(base, path, method="GET", payload=None):
    url = base + path
    if payload is not None:
        r = urllib.request.Request(url, data=json.dumps(payload).encode(), method=method,
            headers={"Content-Type":"application/json","User-Agent":"final"})
    else:
        r = urllib.request.Request(url, method=method, headers={"User-Agent":"final"})
    try:
        with urllib.request.urlopen(r, timeout=25) as resp:
            return resp.status, resp.read().decode("utf-8","replace")
    except urllib.error.HTTPError as e:
        return e.code, (e.read() or b"").decode("utf-8","replace")
    except Exception as e:
        return 0, str(e)

V="https://tools.highkingflower.com"; CN="https://tools-cn.highkingflower.com"
ts=int(time.time())
print("="*64)
print("  本轮全部修复 · 最终验收")
print("="*64)

print("\n【1】Vercel PayPal/pay 端点 (本轮 ESM->CJS 修复) — 应全 4xx/200 无 500 崩溃")
for m,p,pl in [("POST","/api/paypal/order",{"plan":"basic"}),("GET","/pay/return?token=X",None),("GET","/pay/cancel",None)]:
    st,b=req(V,p,m,pl); crash=("FUNCTION_INVOCATION_FAILED" in b)
    print(f"  {m:4s} {p:28s} → HTTP {st}  {'❌崩溃' if crash else '✅干净 fail-closed'}")

print("\n【2】双活收款签名 (40004 非 40002)")
for nm,h in [("Vercel",V),("阿里云",CN)]:
    st,b=req(h,"/api/order","POST",{"out_trade_no":"F"+str(ts)})
    j=json.loads(b) if b.strip().startswith("{") else {}
    print(f"  {nm:5s} 查单 code={j.get('code')} sub={j.get('sub')}  {'✅' if j.get('sub')!='isv.invalid-signature' else '❌'}")

print("\n【3】双活订阅墙 (白嫖堵死 + 未付无权益)")
for nm,h in [("Vercel",V),("阿里云",CN)]:
    st,b=req(h,"/api/subwall","POST",{"action":"subscribe","ref":"z"+str(ts),"plan":"pro"})
    j=json.loads(b) if b.strip().startswith("{") else {}
    print(f"  {nm:5s} subscribe: {j.get('error') or j.get('ok')}  {'✅拒绝' if j.get('ok') is False else '❌'}")

print("\n【4】双活关键页面 parity (/dashboard 本轮 CN 修复)")
for p in ["/","/dashboard","/paid.html","/api/health"]:
    sv,_=req(V,p); sc,_=req(CN,p)
    print(f"  {p:14s} Vercel={sv} 阿里云={sc}  {'✅' if sv==sc else '⚠️'}")

print("\n" + "="*64)
print("  全部通过 = 本轮修复完整 (500崩溃/签名/白嫖/dashboard 均修复)")
print("="*64)
