#!/usr/bin/env bash
# 测 backtest.js 真引擎 (CN): 拉真币安K线 + 算真指标
cd /www/wwwroot/tools-cn.highkingflower.com
echo "=== 1. 直接跑 backtest.js (node 内联) ==="
node -e "
(async()=>{
  const bt=require('./lib/backtest.js');
  const rr=await bt.run({symbol:'BTCUSDT',interval:'1d',limit:90,strategy:'buy_hold'});
  console.log('ok:',rr.ok);
  if(rr.ok){
    console.log('range:',rr.range.start,'~',rr.range.end,'| bars:',rr.bars,'| source:',rr.source);
    console.log('metrics:',JSON.stringify(rr.metrics));
    const rep=bt.buildReport(rr,{strategy_id:'demo_mom'});
    console.log('csv_rows:'); rep.csv_rows.forEach(l=>console.log('  '+l));
    console.log('compliance:',rr.compliance.slice(0,60)+'...');
  } else {
    console.log('error:',rr.error,rr.detail);
  }
})();
" 2>&1
echo ""
echo "=== 2. 测一个不存在的 symbol (应 fail-closed, 不造假) ==="
node -e "
(async()=>{
  const bt=require('./lib/backtest.js');
  const rr=await bt.run({symbol:'FAKEZZZ',limit:10});
  console.log('ok:',rr.ok, '| error:', rr.error||'-', '| detail:', rr.detail||'-');
})();
" 2>&1
echo done
