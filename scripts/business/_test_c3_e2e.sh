#!/usr/bin/env bash
# 端到端测 C3: record 模拟已付费 -> generate 出真回测报告 (CN 需临时 ADMIN_SECRET)
# 先取 CN 现有 env, 临时注入 ADMIN_SECRET 跑, 不永久改
cd /www/wwwroot/tools-cn.highkingflower.com
# 用临时 secret 起一个一次性 node 直接调模块 (不依赖 HTTP 路由)
node -e "
process.env.ADMIN_SECRET='E2E_TEST_ONLY_9x';
(async()=>{
  const rpx=require('./lib/reportexport.js');
  // 模拟已付费解锁 (record)
  const rec=await rpx.record('E2EPAY',{strategy_id:'e2e_demo',format:'pdf',paid_via:'alipay',out_trade_no:'e2e_1',secret:'E2E_TEST_ONLY_9x'});
  console.log('record:',rec.ok,'(unlocked='+ (rec.entry?rec.entry.status:'?') +')');
  // generate 应出真回测报告
  const gen=await rpx.generate('E2EPAY',{strategy_id:'e2e_demo',format:'pdf',symbol:'BTCUSDT',interval:'1d',limit:90});
  console.log('generate ok:',gen.ok,'| report_ready:',gen.report_ready);
  if(gen.report){
    console.log('report.title:',gen.report.title);
    console.log('report.metrics:',JSON.stringify(gen.report.metrics));
    console.log('report.csv_rows:',gen.report.csv_rows.length,'行');
    console.log('report.compliance:',gen.report.compliance.slice(0,50)+'...');
  } else {
    console.log('report: null (引擎不可用? note='+gen.note+')');
  }
  // 清理测试账本
  const fs=require('node:fs/promises');
  try{ await fs.rm(require('path').join(process.env.FILE_STORE_DIR||'/var/lib/bingdashan-cn','reportexport','rpx_E2EPAY.json'),{force:true}); }catch(e){}
  console.log('清理完成');
})();
" 2>&1
echo done
