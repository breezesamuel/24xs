#!/usr/bin/env python3
"""检查 remote main 的 alipay.js 是否含 /api/cashback + cashback record (上一步 cashback.js 推成功, alipay.js 推失败)"""
import subprocess, base64, urllib.parse
REPO = "breezesamuel/24xs"
p = urllib.parse.quote("02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/alipay.js")
r = subprocess.run(["gh","api",f"repos/{REPO}/contents/{p}","-q",".content"], capture_output=True, text=True)
if r.returncode != 0:
    print("gh 取 remote alipay.js 失败:", r.stderr.strip()[:150])
    # 可能远端没有这个文件路径, 或路径不对
    print("(cashback.js 已推成功, alipay.js 路由需单独处理)")
else:
    raw = base64.b64decode(r.stdout).decode("utf-8","replace")
    print("remote alipay.js 行数:", raw.count(chr(10)))
    print("  /api/cashback 路由:", "/api/cashback" in raw)
    print("  cashback.js require:", "cashback.js" in raw)
    print("  cashback record-on-payment:", "cashback.js').record" in raw)
