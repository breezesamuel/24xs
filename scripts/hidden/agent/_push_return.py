#!/usr/bin/env python3
"""重试 push api/pay/return.js (上次失败, 远程还是旧 ESM 版)"""
import subprocess, json, base64, pathlib
REPO="breezesamuel/24xs"; BRANCH="main"
BASE=pathlib.Path(r"F:\2026\24xs")
f="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/pay/return.js"
local=BASE/f
b64=base64.b64encode(local.read_bytes()).decode()
print("本地 return.js 是否已是 CJS:", "require(" in local.read_text(encoding="utf-8") and "import " not in local.read_text(encoding="utf-8").split("\n")[2])
out=subprocess.run(["gh","api",f"repos/{REPO}/contents/{f}?ref={BRANCH}"],capture_output=True,text=True,timeout=30).stdout
sha=json.loads(out).get("sha")
print("远程当前 sha:", sha[:12])
payload={"message":"fix: pay/return.js ESM->CJS (对齐 Vercel type:commonjs, 修 FUNCTION_INVOCATION_FAILED)","branch":BRANCH,"content":b64,"sha":sha,"encoding":"base64"}
proc=subprocess.Popen(["gh","api","-X","PUT",f"repos/{REPO}/contents/{f}","--input","-"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
o,e=proc.communicate(json.dumps(payload),timeout=30)
if proc.returncode==0:
    print("✅ 已推", json.loads(o)["commit"]["sha"][:12])
else:
    print("❌", e[:200], o[:200])
