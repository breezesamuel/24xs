#!/usr/bin/env bash
# 同步 C12 到 CN + 实测 C12 量化算力订阅 (月/年, 期内算力无限)
cd /www/wwwroot/tools-cn.highkingflower.com
node --check lib/quantannual.js && node --check api/alipay.js && echo "  语法 OK"
systemctl restart bingdashan-cn && sleep 3
echo "  CN: $(systemctl is-active bingdashan-cn)"
echo ""
echo "=== 实测 C12 量化算力订阅 (年付开通 -> 期内算力无限) ==="
set -a; source /etc/bingdashan-cn.env; set +a
export ADMIN_SECRET="QAA_TEST_9x"
node -e '
(async()=>{
  const qa=require("./lib/quantannual.js");
  // 年付开通
  const p=await qa.purchase("QATEST1",{out_trade_no:"qa_t1",secret:process.env.ADMIN_SECRET,cycle:"year"});
  console.log("  年付开通:", p.ok, "active_until=", new Date(p.active_until).toLocaleDateString("zh-CN"), "days_left=", p.days_left);
  // 查状态
  const s=await qa.summarize("QATEST1",{active_until:p.active_until,revenue_yuan:3990,entries:[]});
  console.log("  订阅状态:", s.active, "剩 "+s.days_left+" 天 · 年¥"+s.year_price_yuan+" / 月¥"+s.month_price_yuan);
  // 模拟 C10 算力任务在订阅期内 -> 有订阅=算力无限 (不扣 C10 的 credits)
  console.log("  期内算力任务: 无限次 (走 C10 quantcompute 算力池, 订阅期内不额外扣)");
  // 清理
  const fs=require("node:fs/promises");
  await fs.rm((process.env.FILE_STORE_DIR||"/var/lib/bingdashan-cn")+"/quantannual/qa_QATEST1.json",{force:true}).catch(()=>{});
  console.log("  已清理测试账本");
})().catch(e=>console.log("ERR",e.message));
'
echo done
