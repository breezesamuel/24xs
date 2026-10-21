#!/bin/bash
# commit_state.sh — 安全回写 AutoOps 状态到 git（对标 GitHub Actions 最佳实践）
#
# 问题：GitHub Actions 每次都是全新 checkout，编排器状态（state.json / 心跳 /
# 指标）会丢失 → watchdog 永远认为"首跑"。
#
# 方案：每轮结束后把紧凑状态 commit 回仓库。push 失败时自动 reset 到远端 HEAD
# 再重放本地文件（file-level last-writer-wins，在 concurrency group 保护下安全）。

set -u

MSG="${1:-autoops: state sync}"

cd "$(dirname "$0")/../.." || exit 1

# 只回写紧凑状态（不回写大体量原始数据，避免仓库膨胀）
FILES=(
  "autoops/hidden/state.json"
  "autoops/hidden/state/heartbeat.json"
  "autoops/hidden/state/health.json"
  "autoops/hidden/watchdog.jsonl"
  "autoops/hidden/health_status.json"
  "autoops/hidden/alert_state.json"
  "autoops/hidden/real_metrics.jsonl"
  "autoops/hidden/real_alerts.jsonl"
  "autoops/hidden/hidden_plan.json"
  "autoops/hidden/hidden_tasks.jsonl"
)

git config user.name  "autoops-bot" 2>/dev/null || true
git config user.email "autoops@local" 2>/dev/null || true

# 限制 real_metrics.jsonl / watchdog.jsonl / real_alerts.jsonl 体积（只保留末 200 行）
for f in autoops/hidden/real_metrics.jsonl autoops/hidden/watchdog.jsonl autoops/hidden/real_alerts.jsonl; do
  if [ -f "$f" ]; then
    tmp="$(mktemp)"
    tail -n 200 "$f" > "$tmp" && mv "$tmp" "$f"
  fi
done

# 追加暂存
for f in "${FILES[@]}"; do
  [ -f "$f" ] && git add "$f" 2>/dev/null || true
done

if git diff --cached --quiet; then
  echo "[commit_state] no changes to commit"
  exit 0
fi

# 提交 + push，失败则 reset 远端 HEAD 后重放
if git commit -m "$MSG" 2>/dev/null; then
  :
else
  echo "[commit_state] commit failed"
  exit 1
fi

for attempt in 1 2 3; do
  if git push origin HEAD 2>/dev/null; then
    echo "[commit_state] pushed (attempt $attempt)"
    exit 0
  fi
  echo "[commit_state] push failed, resetting to remote HEAD (attempt $attempt)"
  git fetch origin HEAD --quiet 2>/dev/null || true
  git reset --soft FETCH_HEAD 2>/dev/null || true
  # 重新追加（reset --soft 保留暂存）
  for f in "${FILES[@]}"; do
    [ -f "$f" ] && git add "$f" 2>/dev/null || true
  done
  if git diff --cached --quiet; then
    echo "[commit_state] nothing left to commit after reset"
    exit 0
  fi
  git commit -m "$MSG (retry $attempt)" 2>/dev/null || true
done

echo "[commit_state] WARN: push failed after 3 attempts"
exit 0   # 不阻断工作流
