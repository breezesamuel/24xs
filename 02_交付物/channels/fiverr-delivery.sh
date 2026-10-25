#!/usr/bin/env bash
# white-label-deploy.sh — AI 工具站白标一键交付（Fiverr gig 交付引擎）
# 用法: bash white-label-deploy.sh <客户站名> <basic|standard|premium> [输出目录]
#   basic    = 100 tools
#   standard = 1000 tools + 500 games
#   premium  = 5775 tools + 5305 games（全量模板）
# 产物: <输出目录>/<站名>/ 静态站点 + 部署说明；付费墙默认指向客户自己的后端占位。
# 前提: 本机已有 bingdashan 生成器仓库（C:/bingdashan）。

set -euo pipefail
NAME="${1:?usage: white-label-deploy.sh <name> <basic|standard|premium> [outdir]}"
TIER="${2:-standard}"
OUT="${3:-./whitelabel}"
SRC="C:/bingdashan"
STAMP=$(date +%Y%m%d-%H%M)
DEST="$OUT/$NAME"
mkdir -p "$DEST"

echo "== [$STAMP] 白标交付: $NAME ($TIER) =="

# 1) 共享运行时（五语付费墙核心）
cp "$SRC/site/bds-core.js" "$DEST/"
cp "$SRC/site/pricing.html" "$DEST/"

# 2) 工具页（按档位取前 N 个目录）
case "$TIER" in
  basic)    LIMIT=100 ;;
  standard) LIMIT=1000 ;;
  premium)  LIMIT=99999 ;;
  *) echo "unknown tier: $TIER"; exit 1 ;;
esac
i=0
for d in "$SRC"/site/*/; do
  dname=$(basename "$d")
  case "$dname" in
    arcade|api|lib|icons|docs|node_modules|'*') continue ;;
  esac
  [ -f "$d/index.html" ] || continue
  i=$((i+1)); [ "$i" -gt "$LIMIT" ] && break
  cp -r "$d" "$DEST/$dname"
done
echo "tools copied: $((i<LIMIT?i:LIMIT))"

# 3) 游戏页（standard/premium）
if [ "$TIER" != "basic" ]; then
  GLIMIT=$([ "$TIER" = "standard" ] && echo 500 || echo 99999)
  g=0
  for d in "$SRC"/site/arcade/*/; do
    gname=$(basename "$d")
    [ -f "$d/index.html" ] || continue
    g=$((g+1)); [ "$g" -gt "$GLIMIT" ] && break
    mkdir -p "$DEST/arcade"
    cp -r "$d" "$DEST/arcade/$gname"
  done
  cp "$SRC/site/arcade/index.html" "$DEST/arcade/" 2>/dev/null || true
  echo "games copied: $((g<GLIMIT?g:GLIMIT))"
fi

# 4) 客户品牌占位与后端指针
cat > "$DEST/CUSTOMIZE.md" <<EOF
# 客户定制清单（$NAME）
1. 全站替换域名与品牌名（bds-core.js 顶部 BASE/brand + 各页 <title>）
2. 付费墙后端: bds-core.js 的 bdsPayGo() 默认跳 /api/pay —— 配套服务端见
   tool-station-server-pro 包（Basic 档客户需自备，或升级购买）
3. 支付凭证: 按该包 README 的环境变量清单配置（fail-closed，缺配置明确报错）
4. sitemap.xml 用附带的 regenerate 脚本重建后提交 IndexNow
5. 上线自检: /api/health → /api/aliq(40004=签名通过) → /api/verify(cashier:true)
EOF

# 5) 打包
tar czf "$OUT/$NAME-$TIER-$STAMP.tgz" -C "$OUT" "$NAME"
echo "== DONE: $OUT/$NAME-$TIER-$STAMP.tgz =="
ls -la "$OUT/$NAME-$TIER-$STAMP.tgz"
