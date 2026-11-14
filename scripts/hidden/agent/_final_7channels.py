#!/usr/bin/env python3
"""最终: 7 渠道 remote + CN 一致性"""
import urllib.parse, base64, subprocess, json, ssl
REPO = "breezesamuel/24xs"
BASE = "02_交付物/channels/gumroad-product-1/tool-station-server-pro"
files = {
    "lib/cashback.js": "payout",
    "lib/writerewards.js": "quality",
    "lib/bounty.js": "taskCatalog",
    "lib/charity.js": "onPaid",
    "lib/bandwidth.js": "meter",
    "lib/recovery.js": "not_authorized",
    "api/alipay.js": None,
    "channels.html": None,
}
print("=== remote main 7 渠道文件一致性 ===")
for f, marker in files.items():
    p = urllib.parse.quote(BASE + "/" + f)
    r = subprocess.run(["gh","api",f"repos/{REPO}/contents/{p}","-q",".content"], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  {f:20s} 取失败"); continue
    raw = base64.b64decode(r.stdout).decode("utf-8","replace")
    if marker is None:
        if f == "api/alipay.js":
            ok = all(x in raw for x in ['/api/cashback','/api/writerewards','/api/bounty','/api/charity','/api/bandwidth','/api/recovery'])
        else:  # channels.html
            ok = ('赚钱回路' in raw) and ('recovery' in raw.lower())
    else:
        ok = marker in raw
    print(f"  {f:20s} remote {'OK' if ok else 'MISSING'}")
print()
print("=== CN 生产 7 渠道端点 (HTTP) ===")
ctx = ssl.create_default_context()
for e in ["bounty?action=tasks","cashback?action=rate","writerewards?action=rate","charity?action=total","bandwidth?action=rate","recovery?action=rate","config"]:
    try:
        req = urllib.request.Request("https://tools-cn.highkingflower.com/api/"+e, headers={"User-Agent":"Mozilla/5.0"})
        r = urllib.request.urlopen(req, timeout=20, context=ctx)
        print(f"  {e:28s} HTTP {r.status}")
    except urllib.error.HTTPError as ex:
        print(f"  {e:28s} HTTP {ex.code}")
    except Exception as ex:
        print(f"  {e:28s} ERR {type(ex).__name__}")
