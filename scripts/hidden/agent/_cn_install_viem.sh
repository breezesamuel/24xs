#!/usr/bin/env bash
# CN 装 viem + 验证可加载 (实转需要)
cd /www/wwwroot/tools-cn.highkingflower.com
echo "=== 当前是否已可加载 viem ==="
node -e 'try{const v=require("viem");console.log("ALREADY_OK", v.base&&v.base.id);}catch(e){console.log("MISSING", e.code||e.message);} '
echo "=== 装 viem ==="
npm install viem --no-save --loglevel=error 2>&1 | tail -5
echo "=== 再验证 ==="
node -e 'try{const v=require("viem");console.log("NOW_OK base_id=", v.base&&v.base.id, "mainnet_id=", v.mainnet&&v.mainnet.id);}catch(e){console.log("STILL_MISSING", e.code||e.message);} '
echo "done"
