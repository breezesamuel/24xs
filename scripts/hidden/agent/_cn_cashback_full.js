// CN 端 cashback 全链路验证 (scp 传, 避免 heredoc 转义)
const fs = require('fs');
try {
  for (const ln of fs.readFileSync('/etc/bingdashan-cn.env','utf8').split('\n')) {
    if (!ln || ln[0] === '#') continue;
    const i = ln.indexOf('='); if (i>0) process.env[ln.slice(0,i).trim()] = ln.slice(i+1).trim();
  }
} catch(e){}
const cb = require('/www/wwwroot/tools-cn.highkingflower.com/lib/cashback.js');
(async () => {
  const REF = 'CBKSUM2';
  console.log('hasStore:', cb.hasStore());
  const r1 = await cb.record(REF, { out_trade_no:'BDS_S2_1', amount:100, merchant:'jd' });
  const r2 = await cb.record(REF, { out_trade_no:'BDS_S2_2', amount:200, merchant:'tmall' });
  console.log('record:', JSON.stringify({ r1:r1.ok, r1cb:(r1.entry||{}).cashback, r2:r2.ok, r2cb:(r2.entry||{}).cashback }));
  const f = process.env.FILE_STORE_DIR + '/cashback/cbk:' + REF + '.json';
  console.log('文件存在:', fs.existsSync(f), '| 内容:', fs.existsSync(f) ? fs.readFileSync(f,'utf8').slice(0,120) : '(无)');
  const arr = await cb.load(REF);
  console.log('load count:', arr.length, arr.map(e=>e.out_trade_no));
  const sum = cb.summarize(REF, arr);
  console.log('summary:', JSON.stringify({ gross:sum.purchase_gross, cb:sum.cashback_total, can_settle:sum.can_settle }));
  console.log('期望: gross=300 cb=15 can_settle=true');
  // 清理
  try { fs.unlinkSync(f); console.log('已清理'); } catch(e){}
})();
