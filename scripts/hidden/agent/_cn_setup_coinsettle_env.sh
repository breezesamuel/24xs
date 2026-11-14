#!/usr/bin/env bash
# 配 coinsettle live gate (CN): 密钥走文件, live 默认关, 白名单只 demo_user_a, 链默认 Base
# 安全: 不写密钥本身; 只配 _FILE 路径 + 开关; 实转需 owner 手动放密钥文件 + 开 live
ENVF=/etc/bingdashan-cn.env
# 备份
cp "$ENVF" "$ENVF.bak_$(date +%s)"
add_var(){ # add_var KEY=VALUE  (仅追加若不存在)
  if grep -qE "^$1=" "$ENVF" 2>/dev/null; then echo "  $1 已存在, 不覆盖"; else echo "$1=$2" >> "$ENVF"; echo "  已加 $1"; fi
}
# 付款密钥: 读 /etc/coinsettle/payout_key (owner 稍后放, 600 权限); 不在此写密钥
add_var COINBASE_PAYOUT_PRIVATE_KEY_FILE "/etc/coinsettle/payout_key"
# 付款链 (默认 Base)
add_var COINSETTLE_PAYOUT_CHAIN "base"
# 白名单: 只许 demo_user_a 触发打款 (防任意 ref)
add_var COINSETTLE_ALLOW_REFS "demo_user_a"
# live 开关: 默认 false (即使密钥在, 也不实转, 需 owner 显式改 true + 请求带 live=true)
add_var COINSETTLE_CONFIRM_LIVE "false"
echo "=== 当前 coinsettle 相关 env ==="
grep -E "COINSETTLE|COINBASE_PAYOUT" "$ENVF" 2>/dev/null
echo "=== 重启让 env 生效 (不触实转, 因 LIVE=false) ==="
systemctl restart bingdashan-cn && sleep 2 && systemctl is-active bingdashan-cn
echo "done"
