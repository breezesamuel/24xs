// CN 端: 测试 /api/writerewards (写作赚币) 防刷逻辑
const fs = require('fs');
try {
  for (const ln of fs.readFileSync('/etc/bingdashan-cn.env','utf8').split('\n')) {
    if (!ln || ln[0] === '#') continue;
    const i = ln.indexOf('='); if (i>0) process.env[ln.slice(0,i).trim()] = ln.slice(i+1).trim();
  }
} catch(e){}
const wr = require('/www/wwwroot/tools-cn.highkingflower.com/lib/writerewards.js');
(async () => {
  const REF = 'WRTEST';
  console.log('hasStore:', wr.hasStore(), '| store:', storeName());
  const good1 = '这是一篇关于双足机器人拉格朗日动力学建模与增益调度 LQR 控制器设计的技术文章, 详细讨论了倒立摆平衡中的线性化工作点选择、闭环极点配置, 以及支撑相与摆动相切换时 ZMP 轨迹规划的实现细节和数值稳定性验证方法。';
  const good2 = '另一篇不同的内容, 讲支付网关 webhook 验签 (RSA2/SHA256) 与订阅自动开通的可靠性设计, 涵盖幂等性防重放攻击、失败重试留痕、合成探针剔除 (isSynthetic 六层判据) 以及真实营收与测试数据分离的诚实指标体系, 全文涵盖多个工程实践要点。';
  const short = '短';
  const spam = '哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈哈'; // 高重复率
  const r1 = await wr.record(REF, good1, { title:'t1' });
  const r2 = await wr.record(REF, good2, { title:'t2' });
  const r3 = await wr.record(REF, short);
  const r4 = await wr.record(REF, spam);
  const r5 = await wr.record(REF, good1); // 重复 good1 -> duplicate
  console.log('good1:', r1.ok, 'tokens=', r1.entry&&r1.entry.tokens);
  console.log('good2:', r2.ok, 'tokens=', r2.entry&&r2.entry.tokens);
  console.log('short:', r3.ok, r3.error, r3.reasons);
  console.log('spam:', r4.ok, r4.error, r4.reasons);
  console.log('dup good1:', r5.duplicate === true, '(应 true, 不重复给币)');
  const arr = await wr.load(REF);
  console.log('summary:', JSON.stringify(wr.summarize(REF, arr)));
  // 清理
  try { fs.unlinkSync(process.env.FILE_STORE_DIR + '/writerewards/wr:' + REF + '.json'); } catch(e){}
  console.log('已清理');
  function storeName(){ return 'file-store('+(process.env.FILE_STORE_DIR||'none')+')'; }
})();
