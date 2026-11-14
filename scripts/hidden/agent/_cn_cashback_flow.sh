#!/usr/bin/env bash
# CN 端验证 cashback: dotenv? + FILE_STORE_DIR? + in-process record + HTTP summary
set -u
echo "=== CN dotenv ==="
cd /www/wwwroot/tools-cn.highkingflower.com
node -p "try{require.resolve('dotenv');'dotenv OK'}catch(e){'no dotenv'}" 2>&1 | head -1
echo "=== FILE_STORE_DIR ==="
grep '^FILE_STORE_DIR=' /etc/bingdashan-cn.env 2>/dev/null || echo "(未设)"
echo "=== 手动 source env 跑 cashback.record (in-process) ==="
cat > /tmp/_cbk_test.js <<'JSEOF'
// 手动加载 /etc/bingdashan-cn.env (无 dotenv 依赖)
const fs = require('fs');
try {
  const lines = fs.readFileSync('/etc/bingdashan-cn.env','utf8').split('\n');
  for (const ln of lines) {
    if (!ln || ln[0] === '#') continue;
    const i = ln.indexOf('=');
    if (i > 0) process.env[ln.slice(0,i).trim()] = ln.slice(i+1).trim();
  }
} catch(e){}
const cb = require('/www/wwwroot/tools-cn.highkingflower.com/lib/cashback.js');
(async () => {
  const store = cb.hasStore ? 'hasStore=' + cb.hasStore() : '?';
  console.log('store:', store, 'FILE_STORE_DIR=', process.env.FILE_STORE_DIR||'(none)');
  if (!cb.hasStore()) { console.log('无存储, record 会 fail-closed'); process.exit(0); }
  const r1 = await cb.record('CBKTEST1', { out_trade_no: 'BDS_CBKTEST1_1', amount: 100, plan: 'pro', kind: 'sub', merchant: 'jd' });
  const r2 = await cb.record('CBKTEST1', { out_trade_no: 'BDS_CBKTEST1_1', amount: 100, plan: 'pro' });
  const r3 = await cb.record('CBKTEST1', { out_trade_no: 'BDS_CBKTEST1_2', amount: 200, plan: 'pro', merchant: 'taobao' });
  console.log('record:', JSON.stringify({ r1_ok: r1.ok, r1_cb: r1.entry&&r1.entry.cashback, dup: r2.duplicate, r3_ok: r3.ok, r3_cb: r3.entry&&r3.entry.cashback }));
  const arr = await cb.load ? await (async()=>{ const raw = await require('fs').promises ? 'skip' : null })() : null;
  // 用 summarize 读回 (需重新 load)
  const loadArr = await (async () => {
    const raw = await cb['dget'] ? null : null;
    return null;
  })();
  // 直接调内部 summarize (通过 load)
  const arrReal = await cb.load('CBKTEST1');
  const sum = cb.summarize('CBKTEST1', arrReal);
  console.log('summary:', JSON.stringify(sum));
})();
JSEOF
node /tmp/_cbk_test.js 2>&1
echo "=== HTTP ?a=summary&ref=CBKTEST1 ==="
curl -sk "https://tools-cn.highkingflower.com/api/cashback?action=summary&ref=CBKTEST1" --max-time 25 -o /tmp/_cbk_http.txt -w "HTTP %{http_code}\n"
cat /tmp/_cbk_http.txt | head -c 400
echo ""
echo "=== 文件存储是否落盘 ==="
ls -la /opt/bingdashan/data/cashback/ 2>/dev/null | head -5 || echo "(无 /opt/bingdashan/data/cashback 目录)"
echo "=== done ==="
