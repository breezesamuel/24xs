#!/usr/bin/env python3
"""Vercel 主站 7 渠道 + 引流页 最终验证"""
import urllib.request, ssl
ctx = ssl.create_default_context()
base = "https://tools.highkingflower.com"
endpoints = [
    "api/bounty?action=tasks",
    "api/cashback?action=rate",
    "api/writerewards?action=rate",
    "api/charity?action=total",
    "api/bandwidth?action=rate",
    "api/recovery?action=rate",
    "api/config",
]
print("=== Vercel 主站 7 渠道端点 ===")
for e in endpoints:
    try:
        req = urllib.request.Request(base + "/" + e, headers={"User-Agent":"Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=25, context=ctx)
        import json
        try: body = json.loads(r.read().decode())
        except: body = {}
        key = "ok" if isinstance(body, dict) else "?"
        print(f"  /{e:32s} HTTP {r.status} {key}={body.get('ok') if isinstance(body,dict) else '?'}")
    except urllib.error.HTTPError as ex:
        print(f"  /{e:32s} HTTP {ex.code}")
    except Exception as ex:
        print(f"  /{e:32s} ERR {type(ex).__name__}")
# 引流页
try:
    req = urllib.request.Request(base + "/channels.html", headers={"User-Agent":"Mozilla/5.0"})
    r = urllib.request.urlopen(req, timeout=25, context=ctx)
    html = r.read().decode("utf-8","replace")
    print(f"  /channels.html               HTTP {r.status} size={len(html)} 7卡片={'找回' in html and '带宽' in html and '公益' in html}")
except Exception as ex:
    print("  /channels.html ERR", str(ex)[:50])
print()
print("判定: 全 200 + ok:true = Vercel 主站 7 渠道已同步")
