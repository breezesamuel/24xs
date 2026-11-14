#!/usr/bin/env bash
# 同步 C10 到 CN + 实测 C10 量化算力包 (真跑回测 + 扣算力)
cd /www/wwwroot/tools-cn.highkingflower.com
node --check lib/quantcompute.js && node --check api/alipay.js && echo "  语法 OK"
systemctl restart bingdashan-cn && sleep 3
echo "  CN: $(systemctl is-active bingdashan-cn)"
echo ""
echo "=== 实测 C10 量化算力包 (真跑回测 + 扣算力 credits) ==="
set -a; source /etc/bingdashan-cn.env; set +a
export ADMIN_SECRET="QC_TEST_9x"
node -e '
(async()=>{
  const qc=require("./lib/quantcompute.js");
  // 模拟已付费 (purchase 20 credits)
  const p=await qc.purchase("QCTEST1",{out_trade_no:"qc_t1",secret:process.env.ADMIN_SECRET});
  console.log("  purchase:", p.ok, "credits_left=", p.credits_left);
  // 跑一次真回测算力任务
  const r=await qc.run("QCTEST1",{task:"backtest",symbol:"BTCUSDT",interval:"1d",limit:180});
  if(r.ok){
    const m=r.results[0].metrics;
    console.log("  C10 算力回测 (真数据):");
    console.log("    BTCUSDT: 收益 "+m.total_return_pct+"% · 夏普 "+m.sharpe+" · 回撤 -"+m.max_drawdown_pct+"% · 胜率 "+m.win_rate_pct+"%");
    console.log("    扣算力: "+r.credits_used+" · 剩 "+r.credits_left+" credits");
    console.log("    合规:", r.compliance.disclaimer.slice(0,40)+"...");
  } else {
    console.log("  C10 失败:", r.error, r.detail||"");
  }
  // 再跑一次 optimize (参数网格, 3 credits)
  const r2=await qc.run("QCTEST1",{task:"optimize",symbol:"BTCUSDT",grid:[{interval:"1d",limit:60},{interval:"1d",limit:120}]});
  if(r2.ok){
    console.log("  C10 算力优化批次: "+r2.results.length+" 组 · 扣 "+r2.credits_used+" · 剩 "+r2.credits_left);
  }
  const fs=require("node:fs/promises");
  await fs.rm((process.env.FILE_STORE_DIR||"/var/lib/bingdashan-cn")+"/quantcompute/qc_QCTEST1.json",{force:true}).catch(()=>{});
  console.log("  已清理测试账本");
})().catch(e=>console.log("ERR",e.message));
'
echo done
