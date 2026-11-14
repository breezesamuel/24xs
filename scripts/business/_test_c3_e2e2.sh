#!/usr/bin/env bash
# E2E 测 C3: 带 CN 真实 env (source /etc/bingdashan-cn.env) + 临时 ADMIN_SECRET
cd /www/wwwroot/tools-cn.highkingflower.com
set -a; source /etc/bingdashan-cn.env; set +a
export ADMIN_SECRET="E2E_TEST_ONLY_9x"
node -e '
(async()=>{
  const rpx=require("./lib/reportexport.js");
  const rec=await rpx.record("E2EPAY",{strategy_id:"e2e_demo",format:"pdf",paid_via:"alipay",out_trade_no:"e2e_1",secret:process.env.ADMIN_SECRET});
  console.log("record:",rec.ok,"(status="+ (rec.entry?rec.entry.status:"?") +")");
  const gen=await rpx.generate("E2EPAY",{strategy_id:"e2e_demo",format:"pdf",symbol:"BTCUSDT",interval:"1d",limit:90});
  console.log("generate ok:",gen.ok,"| report_ready:",gen.report_ready);
  if(gen.report){
    console.log("  title:",gen.report.title);
    console.log("  metrics:",JSON.stringify(gen.report.metrics));
    console.log("  csv:",gen.report.csv_rows.length,"行 · compliance:",gen.report.compliance.slice(0,40)+"...");
  }
  // 清理
  const fs=require("node:fs/promises"); const p=require("path");
  await fs.rm(p.join(process.env.FILE_STORE_DIR,"reportexport","rpx_E2EPAY.json"),{force:true}).catch(()=>{});
  console.log("已清理测试账本");
})().catch(e=>console.log("ERR",e.message));
' 2>&1
echo done
