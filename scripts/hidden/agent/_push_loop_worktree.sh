#!/usr/bin/env bash
# 干净推 loop: 新建分支基于 remote main, 只改 autoops.js, commit, push (绕 CJK merge 卡顿)
cd /f/2026/24xs
REPO=breezesamuel/24xs
F="02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/autoops.js"
# 1. 备份本地 loop 版 autoops.js
cp "$F" /tmp/_autoops_loop.js
# 2. 建临时 worktree 基于 origin/main (干净)
git fetch origin main 2>&1 | tail -1
git worktree add --no-checkout /tmp/_loop_wt origin/main 2>&1 | tail -2
git -C /tmp/_loop_wt checkout -f main 2>&1 | tail -1
# 把 loop 版 autoops.js 放进 worktree
cp /tmp/_autoops_loop.js "/tmp/_loop_wt/$F"
git -C /tmp/_loop_wt add "$F" 2>&1 | tail -1
git -C /tmp/_loop_wt -c user.name="bingdashan-agent" -c user.email="agent@24xs.local" commit -m "feat: money-loop funnel + reconciliation (?a=loop)" 2>&1 | tail -2
# 3. 推到 origin main
git -C /tmp/_loop_wt push origin main 2>&1 | tail -4
# 4. 清理
git worktree remove --force /tmp/_loop_wt 2>&1 | tail -1
echo "=== 验证 remote ==="
python - <<'PY'
import subprocess, base64, urllib.parse
p = urllib.parse.quote("02_交付物/channels/gumroad-product-1/tool-station-server-pro/api/autoops.js")
r = subprocess.run(["gh","api",f"repos/breezesamuel/24xs/contents/{p}","-q",".content"], capture_output=True, text=True)
if r.returncode==0:
    raw = base64.b64decode(r.stdout).decode("utf-8","replace")
    print("remote loopStats:", raw.count("loopStats"), "| 'loop' 分支:", ("'loop'" in raw))
else:
    print("取 remote 失败:", r.stderr[:100])
PY
echo "=== done ==="
