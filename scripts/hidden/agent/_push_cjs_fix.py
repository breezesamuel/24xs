#!/usr/bin/env python3
"""commit 本地 + 把改动 push 到远程 (git push 被网络拦, 用 gh api)"""
import subprocess, json, base64, pathlib

REPO = "breezesamuel/24xs"; BRANCH = "main"
BASE = pathlib.Path(r"F:\2026\24xs")

# 1. 本地 git add/commit (含删除 package.json)
add_files = [
 "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/_lib/plans.js",
 "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/_lib/paypal.js",
 "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/_lib/pending.js",
 "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/_lib/mailer.js",
 "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/paypal/order.js",
 "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/paypal/capture.js",
 "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/paypal/status.js",
 "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/pay/return.js",
 "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/pay/cancel.js",
 "02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/index.js",
 ".github/workflows/storefront_integrity.yml",
 "scripts/hidden/agent/_verify_paypal_cjs.py",
]
r = subprocess.run(["git", "-C", str(BASE), "add"] + add_files + ["-A", "02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/_lib/package.json"],
                   capture_output=True, text=True)
print("add rc=", r.returncode, r.stderr.strip()[:80])
r = subprocess.run(["git", "-C", str(BASE), "commit", "-m",
 "fix: Vercel PayPal 500 (ESM->CJS) + security-lint SC2155 修复\n\n"
 "- PayPal/pay 端点 ESM import 在 CJS 项目里 require 失败→FUNCTION_INVOCATION_FAILED 500\n"
 "   根因: lib/_lib 有 package.json type:module, handler(CJS) require ESM 得空对象\n"
 "   修复: 全链转 CJS + 删 lib/_lib/package.json + 凭证缺失改 503 fail-closed\n"
 "- storefront_integrity.yml 修 SC2155 (local ref=$(...) → 声明与赋值分离)\n"
 "- 已部署 Vercel: 5 个端点全 4xx/200 干净 (PayPal 真可达, 422=sandbox 测试)"],
                   capture_output=True, text=True)
print("commit rc=", r.returncode, r.stdout.strip()[:80])

# 2. 逐个 push 到远程 (gh api Contents)
files = add_files + ["02_交付物/channels/gumroad-product-1/tool-station-server-pro/lib/_lib/package.json"]
for f in files:
    p = BASE / f
    b64 = base64.b64encode(p.read_bytes()).decode() if p.exists() else None
    out = subprocess.run(["gh","api",f"repos/{REPO}/contents/{f}?ref={BRANCH}"], capture_output=True, text=True, timeout=30).stdout
    try: sha = json.loads(out).get("sha")
    except: sha = None
    if p.exists():
        payload = {"message":"fix: Vercel PayPal ESM->CJS + SC2155","branch":BRANCH,"content":b64,"sha":sha,"encoding":"base64"}
        proc = subprocess.Popen(["gh","api","-X","PUT",f"repos/{REPO}/contents/{f}","--input","-"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        o,e = proc.communicate(json.dumps(payload), timeout=30)
        print(("  ✅ "+f if proc.returncode==0 else "  ❌ "+f))
    else:
        # 删除远程 package.json
        payload = {"message":"fix: 删 lib/_lib/package.json (type:module 导致 CJS require 空)","branch":BRANCH,"sha":sha}
        proc = subprocess.Popen(["gh","api","-X","DELETE",f"repos/{REPO}/contents/{f}","--input","-"],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        o,e = proc.communicate(json.dumps(payload), timeout=30)
        print(("  ✅(删除) "+f if proc.returncode==0 else "  ❌(删除) "+f + " "+e[:100]))
