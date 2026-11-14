// CN 端: HTTP ?a=cashback 端点全链路 (record 通过 in-process, summary/settle 通过 HTTP)
const fs = require('fs');
try {
  for (const ln of fs.readFileSync('/etc/bingdashan-cn.env','utf8').split('\n')) {
    if (!ln || ln[0] === '#') continue;
    const i = ln.indexOf('='); if (i>0) process.env[ln.slice(0,i).trim()] = ln.slice(i+1).trim();
  }
} catch(e){}
const cb = require('/www/wwwroot/tools-cn.highkingflower.com/lib/cashback.js');
const https = require('https');
function get(path){ return new Promise((res,rej)=>{ https.get({host:'tools-cn.highkingflower.com',port:443,path,headers:{'User-Agent':'test'},rejectUnauthorized:false}, r=>{ let d=''; r.on('data',c=>d+=c); r.on('end',()=>res({code:r.statusCode,body:d})); }).on('error',rej); }); }
(async () => {
  const REF = 'CBKHTTP';
  await cb.record(REF, { out_trade_no:'BDS_H_1', amount: 150, merchant:'meituan' });  // 5% = 7.5
  // 1. HTTP ?a=rate
  let r = await get('/api/cashback?action=rate');
  console.log('1. ?a=rate:', r.code, r.body.slice(0,100));
  // 2. HTTP ?a=summary&ref=CBKHTTP (应看到 1 条, cashback=7.5, 未达 10 门槛 can_settle=false)
  r = await get('/api/cashback?action=summary&ref=' + REF);
  let j = JSON.parse(r.body);
  console.log('2. ?a=summary:', r.code, JSON.stringify({ store:j.store, count:j.count, cb:j.cashback_total, can_settle:j.can_settle }));
  // 3. HTTP ?a=settle 无 secret (应 403 fail-closed)
  r = await get('/api/cashback?action=settle&ref=' + REF);
  console.log('3. ?a=settle 无 key:', r.code, r.body.slice(0,80));
  // 4. 加一笔到超过门槛, 再 settle (仍无 secret, 应 403)
  await cb.record(REF, { out_trade_no:'BDS_H_2', amount: 200, merchant:'dianping' });  // +10
  r = await get('/api/cashback?action=summary&ref=' + REF);
  j = JSON.parse(r.body);
  console.log('4. summary(2条):', JSON.stringify({ count:j.count, cb:j.cashback_total, can_settle:j.can_settle }));
  // 清理
  try { fs.unlinkSync(process.env.FILE_STORE_DIR + '/cashback/cbk:' + REF + '.json'); } catch(e){}
  console.log('已清理测试数据');
})();
