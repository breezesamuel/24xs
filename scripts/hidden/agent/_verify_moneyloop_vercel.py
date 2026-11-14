#!/usr/bin/env python3
"""Vercel 生产: 确认刚建的 MONELOOP_1 订单进了 KV 账本 (赚钱回路: 建单->账本)。
读 Vercel AUTOOPS_SECRET (vercel env pull), 调 ?a=loop 看 orders 是否含 MONELOOP_1。"""
import subprocess, json, os, urllib.request, ssl
# 从 vercel env 取 AUTOOPS_SECRET (vercel env pull 到临时目录)
envdir = "F:/2026/24xs/scripts/hidden/agent/_loop_env"
subprocess.run(["vercel","env","pull",envdir,"--scope","solmount","--project","bingdashan-pain-tools","--yes"],
               capture_output=True, text=True, timeout=120)
env = {}
try:
    for stage in ("production","preview","development"):
        f = os.path.join(envdir, f".vercel", "env", stage, ".env")
        if os.path.exists(f):
            for ln in open(f, encoding="utf-8"):
                if "=" in ln and ln.startswith(("AUTOOPS_SECRET","KV_","UPSTASH")):
                    k,v = ln.strip().split("=",1); env[k]=v
except Exception as e:
    print("env pull:", e)
# Vercel 站点 secret 值在 pull 时可能 [SENSITIVE]; 试直接读
secret = env.get("AUTOOPS_SECRET","")
print("AUTOOPS_SECRET 取到:", (secret[:8]+'...' if len(secret)>10 else '(空/SENSITIVE)'))
ctx = ssl.create_default_context()
# 1. 先确认 MONELOOP_1 在 Vercel KV (bds_order_)
url = f"https://tools.highkingflower.com/api/aliq?out_trade_no=BDS_MONELOOP_1_trial_1794372592609"
try:
    r = urllib.request.urlopen(url, timeout=25, context=ctx)
    j = json.loads(r.read().decode())
    print("Vercel /api/aliq 查单 MONELOOP_1:", j.get("ok"), "result_code=", j.get("result",{}).get("code") if isinstance(j.get("result"),dict) else j.get("result"))
except Exception as e:
    print("aliq:", type(e).__name__, str(e)[:60])
# 2. ?a=loop (若有 secret)
if secret and "SENSITIVE" not in secret:
    try:
        r = urllib.request.urlopen(f"https://tools.highkingflower.com/api/autoops.js?a=loop&k={secret}", timeout=30, context=ctx)
        j = json.loads(r.read().decode())
        print("Vercel ?a=loop:", json.dumps(j.get("loop",{}).get("funnel",{}), ensure_ascii=False)[:200])
    except Exception as e:
        print("?a=loop:", type(e).__name__, str(e)[:60])
else:
    print("(Vercel secret 是 [SENSITIVE], 需 owner 在 Vercel dashboard 设明文或手动调用 ?a=loop)")
