#!/usr/bin/env bash
# 同步 C7/C8 到 CN + 重启 + 实测 C7 过拟合检测 (真出 verdict)
cd /www/wwwroot/tools-cn.highkingflower.com
echo "=== 1. 校验 + 重启 ==="
node --check lib/overfitcheck.js && node --check lib/whitebox.js && node --check api/alipay.js && echo "  语法 OK"
systemctl restart bingdashan-cn && sleep 3
echo "  CN: $(systemctl is-active bingdashan-cn)"
echo ""
echo "=== 2. 实测 C7 过拟合检测 (真跑, 喂真 K 线, 出 verdict) ==="
set -a; source /etc/bingdashan-cn.env; set +a
export ADMIN_SECRET="OFC_TEST_9x"
node -e '
(async()=>{
  const ofc=require("./lib/overfitcheck.js");
  // 模拟已付费 (purchase 5 次)
  const p=await ofc.purchase("OFCP1",{strategy_id:"test",out_trade_no:"ofc_t1",secret:process.env.ADMIN_SECRET});
  console.log("  purchase:", p.ok, "quota_left=", p.quota_left);
  // 跑一次真过拟合检测
  const r=await ofc.run("OFCP1",{symbol:"BTCUSDT",interval:"1d",limit:180});
  if(r.ok){
    console.log("  C7 检测结果:");
    console.log("    区间:", r.result.range.start,"~",r.result.range.end,"· bars",r.result.metrics.bars||r.result.metrics);
    console.log("    总收益%:", r.result.metrics.total_return_pct, "| Sharpe:", r.result.metrics.sharpe, "| 最大回撤%:", r.result.metrics.max_drawdown_pct, "| 胜率%:", r.result.metrics.win_rate_pct);
    console.log("    过拟合风险:", r.result.overfit.risk_level, "(score", r.result.overfit.risk_score, ")");
    console.log("    结论:", r.result.verdict);
    console.log("    合规:", r.result.compliance.disclaimer.slice(0,40)+"...");
  } else {
    console.log("  C7 检测失败:", r.error, r.detail||"");
  }
  // 清理
  const fs=require("node:fs/promises");
  await fs.rm((process.env.FILE_STORE_DIR||"/var/lib/bingdashan-cn")+"/overfitcheck/ofc_OFCP1.json",{force:true}).catch(()=>{});
  console.log("  已清理测试账本");
})().catch(e=>console.log("ERR",e.message));
'
echo done
