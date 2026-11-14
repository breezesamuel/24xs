#!/usr/bin/env bash
cd /www/wwwroot/tools-cn.highkingflower.com
node -e '
process.env.ADMIN_SECRET="E2E_TEST_ONLY_9x";
(async()=>{
  const rpx=require("./lib/reportexport.js");
  const rec=await rpx.record("E2EPAY",{strategy_id:"e2e_demo",format:"pdf",paid_via:"alipay",out_trade_no:"e2e_1",secret:"E2E_TEST_ONLY_9x"});
  console.log("record:",JSON.stringify(rec));
  console.log("hasStore:",rpx.hasStore());
  const fs=require("node:fs"); const dir=process.env.FILE_STORE_DIR;
  console.log("FILE_STORE_DIR:",dir, dir?fs.existsSync(dir):"-");
})().catch(e=>console.log("ERR",e.message));
' 2>&1
echo "=== 若 record 因 hasStore=false 失败, 看 CN 的 FILE_STORE_DIR ==="
grep -E "FILE_STORE_DIR" /etc/bingdashan-cn.env 2>/dev/null || echo "  /etc/bingdashan-cn.env 无 FILE_STORE_DIR"
echo "=== CN 服务进程实际 env (systemctl show) ==="
systemctl show bingdashan-cn -p EnvironmentFile 2>/dev/null
echo done
