#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
const viem=require("viem");
// 完整导出清单: 找所有与 本地签名/地址派生 相关的 API
const keys=Object.keys(viem).sort();
const interesting=keys.filter(k=>/private|public|sign|account|address|wallet|localSign|toAddress|getAddress/i.test(k));
console.log("=== viem 导出总数: "+keys.length);
console.log("=== 相关 API: "+interesting.join(", "));
// 逐个看类型
interesting.forEach(k=>{ if(typeof viem[k]==="function") console.log("  fn "+k); });
// 特别检查
["privateKeyToAccount","toAccount","publicToAccount","getAddress","secp256k1GetPublicKey","keccak256","createWalletClient","signMessage","localAccount","account"].forEach(k=>{
  console.log("  check "+k+": "+typeof viem[k]);
});
' 2>&1 | head -30
