// CN 端: 测试 /api/bounty (劳动换币) 防刷 + 任务目录
const fs = require('fs');
try {
  for (const ln of fs.readFileSync('/etc/bingdashan-cn.env','utf8').split('\n')) {
    if (!ln || ln[0] === '#') continue;
    const i = ln.indexOf('='); if (i>0) process.env[ln.slice(0,i).trim()] = ln.slice(i+1).trim();
  }
} catch(e){}
const by = require('/www/wwwroot/tools-cn.highkingflower.com/lib/bounty.js');
(async () => {
  console.log('hasStore:', by.hasStore());
  console.log('任务目录:', by.taskCatalog().map(t=>t.id+'(奖'+t.reward+',证'+t.proof_min+')').join(', '));
  const REF = 'BYTEST';
  // 1. 未知任务
  const r0 = await by.claim(REF, 'no_such_task', 'some proof text that is long enough to pass min');
  console.log('未知任务:', r0.ok, r0.error);
  // 2. 证据太短
  const r1 = await by.claim(REF, 'by_introduce', '短');
  console.log('证据太短:', r1.ok, r1.error, 'need='+r1.need);
  // 3. 正常完成 by_introduce (证明 >= 20 字)
  const r2 = await by.claim(REF, 'by_introduce', '我已向 3 位朋友介绍了这个双足机器人项目, 他们都表示感兴趣并注册试用了。');
  console.log('正常完成 by_introduce:', r2.ok, 'tokens=', r2.entry && r2.entry.reward, '| 应 =', by.taskCatalog()[0].reward);
  // 4. 重复领取同任务同证据 -> duplicate
  const r3 = await by.claim(REF, 'by_introduce', '我已向 3 位朋友介绍了这个双足机器人项目, 他们都表示感兴趣并注册试用了。');
  console.log('重复领取:', r3.duplicate === true ? 'duplicate=true (不重复给币 ✅)' : 'FAIL: ' + JSON.stringify(r3));
  // 5. 完成 by_review (需 >=200 字证明)
  const r4 = await by.claim(REF, 'by_review', 'x'.repeat(210));
  console.log('by_review (200字证):', r4.ok, r4.error, 'tokens=', r4.entry && r4.entry.reward, '(应为 by_introduce*2)');
  const arr = await by.load(REF);
  console.log('summary:', JSON.stringify(by.summarize(REF, arr)));
  // 清理
  try { fs.unlinkSync(process.env.FILE_STORE_DIR + '/bounty/by:' + REF + '.json'); } catch(e){}
  console.log('已清理测试数据');
})();
