#!/usr/bin/env bash
# CN: 确认 ethers 装了 + 设 COINSETTLE_PAYOUT_ADDRESS + 同步 alipay.js + 重启
cd /www/wwwroot/tools-cn.highkingflower.com
echo "=== ethers 是否已 require 到 ==="
node -e 'try{require("ethers");console.log("  ethers OK")}catch(e){console.log("  ethers 需装: "+e.code)}'
# 同步 alipay.js (由本地 scp 已放好, 这里只校验语法 + 重启)
node --check /www/wwwroot/tools-cn.highkingflower.com/api/alipay.js && echo "  alipay.js 语法 OK"
# 设 PAYOUT_ADDRESS (0x0913... 我们派生的付款地址)
if ! grep -qE '^COINSETTLE_PAYOUT_ADDRESS=' /etc/bingdashan-cn.env; then
  echo 'COINSETTLE_PAYOUT_ADDRESS=0x09132f96436ae12ecc4884241fc030cefecedcf8' >> /etc/bingdashan-cn.env
  echo "  已加 COINSETTLE_PAYOUT_ADDRESS"
fi
echo "  当前 coinsettle env:"
grep -E '^COINSETTLE|^COINBASE_PAYOUT' /etc/bingdashan-cn.env 2>/dev/null
systemctl restart bingdashan-cn && sleep 2 && systemctl is-active bingdashan-cn && echo "  重启 OK"
