#!/usr/bin/env bash
# 测 CN 6 渠道端点 (charity + bandwidth 新增) + 防刷逻辑
echo "=== 1. 6 渠道端点全 200? ==="
for e in "bounty?action=tasks" "cashback?action=rate" "writerewards?action=rate" "charity?action=total" "bandwidth?action=rate" "config"; do
  printf "  %s: " "$e"; curl -sk "https://tools-cn.highkingflower.com/api/$e" --max-time 20 -o /dev/null -w "HTTP %{http_code}\n"
done
echo "=== 2. 公益: 记一笔捐赠 (in-process 验证, 经 ?a=donate 走 HTTP) ==="
curl -sk "https://tools-cn.highkingflower.com/api/charity?action=donate" --max-time 20 \
  -H "Content-Type: application/json" -X POST \
  -d '{"ref":"CHARITYTEST","amount":50,"project":"education"}' | head -c 160; echo
echo "  总账:"; curl -sk "https://tools-cn.highkingflower.com/api/charity?action=total" --max-time 20 | head -c 200; echo
echo "=== 3. 公益: 金额非法 (0 / 999999) ==="
curl -sk "https://tools-cn.highkingflower.com/api/charity?action=donate" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"X","amount":0}' | head -c 80; echo " (0 应拒)"
curl -sk "https://tools-cn.highkingflower.com/api/charity?action=donate" --max-time 20 -H "Content-Type: application/json" -X POST -d '{"ref":"X","amount":999999}' | head -c 80; echo " (超额应拒)"
echo "=== 4. 带宽: meter 上报 (in-process) ==="
cat > /tmp/_bw_test.js <<'JSEOF'
const fs=require('fs');
try{for(const ln of fs.readFileSync('/etc/bingdashan-cn.env','utf8').split('\n')){if(!ln||ln[0]==='#')continue;const i=ln.indexOf('=');if(i>0)process.env[ln.slice(0,i).trim()]=ln.slice(i+1).trim();}}catch(e){}
const bw=require('/www/wwwroot/tools-cn.highkingflower.com/lib/bandwidth.js');
(async()=>{
  console.log('hasStore:',bw.hasStore());
  const r1=await bw.meter('BWTEST', 20, {gbs:2, source:'client'});
  console.log('meter 20GB:', r1.ok, 'tokens=', r1.entry&&r1.entry.tokens, '(20*0.5=10)');
  const r2=await bw.meter('BWTEST', 60, {});  // 超日上限 50 -> 拒
  console.log('meter 60GB(超cap):', r2.ok, r2.error, 'cap='+r2.cap);
  const arr=await bw.load('BWTEST');
  console.log('summary:', JSON.stringify(bw.summarize('BWTEST',arr)));
  try{fs.unlinkSync(process.env.FILE_STORE_DIR+'/bandwidth/bw:BWTEST.json');}catch(e){}
  console.log('已清理');
})();
JSEOF
node /tmp/_bw_test.js 2>&1
echo "=== 5. 清理公益测试数据 ==="
rm -f /var/lib/bingdashan-cn/charity/dy:CHARITYTEST.json /var/lib/bingdashan-cn/charity/dy:total.json 2>/dev/null
echo "done"
