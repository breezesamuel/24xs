#!/usr/bin/env python3
"""4 渠道最终一致性: remote main + 本地 commit"""
import urllib.parse, base64, subprocess, os
REPO = "breezesamuel/24xs"
BASE = "02_交付物/channels/gumroad-product-1/tool-station-server-pro"
checks = {
    "lib/cashback.js": "payout",
    "lib/writerewards.js": "quality",
    "lib/bounty.js": "taskCatalog",
    "api/alipay.js": None,   # 特殊: 查 3 路由
}
print("=== remote main 4 文件一致性 ===")
for f, marker in checks.items():
    p = urllib.parse.quote(BASE + "/" + f)
    r = subprocess.run(["gh","api",f"repos/{REPO}/contents/{p}","-q",".content"], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  {f:22s} remote 取失败: {r.stderr.strip()[:50]}")
        continue
    raw = base64.b64decode(r.stdout).decode("utf-8","replace")
    if marker is None:
        ok = ("/api/bounty" in raw) and ("/api/cashback" in raw) and ("/api/writerewards" in raw)
    else:
        ok = marker in raw
    print(f"  {f:22s} remote {'OK' if ok else 'MISSING'} ({len(raw)} 字符)")
print("=== 本地最近 commit ===")
r = subprocess.run(["git","log","--oneline","-3","--format=%h %s"], cwd="F:/2026/24xs", capture_output=True, text=True)
print(r.stdout)
