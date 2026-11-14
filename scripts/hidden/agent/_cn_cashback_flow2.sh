#!/usr/bin/env bash
# 干净的 cashback record->summary 全链路 (CN 文件存储)
cd /www/wwwroot/tools-cn.highkingflower.com
cat > /tmp/_cbk2.js <<'JSEOF'
const fs = require('fs');
try {
  for (const ln of fs.readFileSync('/etc/bingdashan-cn.env','utf8').split('\n')) {
    if (!ln || ln[0] === '#') continue;
    const i = ln.indexOf('='); if (i > 0) process.env[ln.slice(0,i).trim()] = ln.slice(i+1).trim();
  }
} catch(e){}
const cb = require('/www/wwwroot/tools-cn.highkingflower.com/lib/cashback.js');
(async () => {
  console.log('hasStore:', cb.hasStore());
  if (!cb.hasStore()) { console.log('无存储, fail-closed'); return; }
  const r1 = await cb.record('CBKTEST', { out_trade_no: 'BDS_CBK_1', amount: 100, plan: 'pro', merchant: 'jd' });
  const r2 = await cb.record('CBKTEST', { out_trade_no: 'BDS_CBK_1', amount: 100, plan: 'pro' });  // 幂等
  const r3 = await cb.record('CBKTEST', { out_trade_no: 'BDS_CBK_2', amount: 200, plan: 'pro', merchant: 'taobao' });
  console.log('records:', JSON.stringify({ r1: r1.ok, cb1: r1.entry&&r1.entry.cashback, dup: r2.duplicate, r3: r3.ok, cb3: r3.entry&&r3.entry.cashback }));
  const arr = await cb.load('CBKTEST');
  const sum = cb.summarize('CBKTEST', arr);
  console.log('summary:', JSON.stringify(sum));
  // settle 需 admin secret (fail-closed, 这里只验证门槛判断)
  console.log('can_settle:', sum.can_settle, '(total=' + sum.cashback_total + ' >= 10? ', sum.cashback_total >= 10, ')');
})();
JSEOF
node /tmp/_cbk2.js 2>&1
echo "=== 文件落盘验证 ==="
ls -la /var/lib/bingdashan-cn/cashback/ 2>/dev/null | head -6 || echo "(无 cashback 子目录 - 检查 FILE_STORE_DIR)"
echo "=== 清理测试数据 (不留脏数据) ==="
rm -f /var/lib/bingdashan-cn/cashback/cbk:CBKTEST.json /var/lib/bingdashan-cn/cashback/*CBKTEST* 2>/dev/null
echo "done"
