#!/usr/bin/env bash
# 同步 C9 到 CN + 实测 C9 多资产纸面组合 (真数据)
cd /www/wwwroot/tools-cn.highkingflower.com
node --check lib/papercombo.js && node --check api/alipay.js && echo "  语法 OK"
systemctl restart bingdashan-cn && sleep 3
echo "  CN: $(systemctl is-active bingdashan-cn)"
echo ""
echo "=== 实测 C9 多资产纸面组合 (BTC/ETH/SOL 真 K 线) ==="
set -a; source /etc/bingdashan-cn.env; set +a
export ADMIN_SECRET="PC_TEST_9x"
node -e '
(async()=>{
  const pc=require("./lib/papercombo.js");
  const p=await pc.purchase("PCT1",{out_trade_no:"pc_t1",secret:process.env.ADMIN_SECRET});
  console.log("  purchase:",p.ok,"slots_left=",p.slots_left);
  const r=await pc.runCombo("PCT1",{legs:["BTCUSDT","ETHUSDT","SOLUSDT"],interval:"1d",limit:90});
  if(r.ok){
    console.log("  C9 纸面组合 (真数据, 非实盘):");
    r.combo.legs.forEach(l=>console.log("    "+l.symbol+": 收益"+l.total_return_pct+"% 夏普"+l.sharpe+" 回撤-"+l.max_dd_pct+"% 胜率"+l.win_rate_pct+"%"));
    const w=r.combo.weighted;
    console.log("    组合净值 "+w.final_value_x+"x · 收益 "+(w.total_return_pct>0?"+":"")+w.total_return_pct+"% · 夏普 "+w.sharpe+" · 最差回撤 -"+w.worst_max_dd_pct+"%");
    console.log("    合规:", r.compliance.disclaimer.slice(0,50)+"...");
  } else {
    console.log("  C9 失败:", r.error, r.detail||"");
  }
  const fs=require("node:fs/promises");
  await fs.rm((process.env.FILE_STORE_DIR||"/var/lib/bingdashan-cn")+"/papercombo/pc_PCT1.json",{force:true}).catch(()=>{});
  console.log("  已清理测试账本");
})().catch(e=>console.log("ERR",e.message));
'
echo done
