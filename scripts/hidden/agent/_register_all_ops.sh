#!/bin/bash
# 一次把 25 个运营端点 (20 + 5) 全部加入 FLOW_OPS (基于语法 OK 的当前文件)
P=/opt/bingdashan/core/paywall.js
cp "$P" "$P.bak.$(date +%s)" 2>/dev/null
python3 - "$P" <<'PYEOF'
import sys,re
p=sys.argv[1]; s=open(p,encoding="utf-8").read()
additions=[
 ("POST /v1/ledger/purge","账本清理执行（运营侧，需管理令牌）"),
 ("POST /v1/ledger/writeoff-stale","陈旧账核销（运营侧，需管理令牌）"),
 ("POST /v1/ledger/clean","账本清理（运营侧，需管理令牌）"),
 ("GET /v1/stresslab/board","压测看板（运营侧，需管理令牌）"),
 ("POST /v1/stresslab/run","压测运行（运营侧，需管理令牌）"),
 ("GET /v1/capacity/board","容量看板（运营侧，需管理令牌）"),
 ("POST /v1/capacity/plan","容量规划（运营侧，需管理令牌）"),
 ("GET /v1/storage-engine","存储引擎状态（运营侧，需管理令牌）"),
 ("GET /v1/dataq/board","数据质量看板（运营侧，需管理令牌）"),
 ("GET /v1/dataq/ask","数据问答（运营侧，需管理令牌）"),
 ("POST /v1/dataq/ask","数据问答提交（运营侧，需管理令牌）"),
 ("GET /v1/dataq-sql/board","SQL 数据看板（运营侧，需管理令牌）"),
 ("POST /v1/dataq-sql/ask","SQL 问答（运营侧，需管理令牌）"),
 ("POST /v1/dataq-sql/execute","SQL 执行（运营侧，需管理令牌）"),
 ("POST /v1/hw/command","硬件命令（宿主能力，需管理令牌+限频）"),
 ("GET /v1/business-loop","业务闭环体检（运营侧，需管理令牌）"),
 ("GET /v1/free-tier/board","免费额度看板（运营侧，需管理令牌）"),
 ("GET /v1/free-tier/daily","免费额度日报（运营侧，需管理令牌）"),
 ("GET /v1/agent-flows","Agent 流程列表（运营侧）"),
 ("GET /v1/agent-flows/render","Agent 流程渲染（运营侧）"),
 ("POST /v1/subs/free-trial","免费试用领取（客户免费入口, 每人一次+IP限频, 非付费价值）"),
 ("POST /v1/care/profile/migrate","客户档案加密迁移（运营侧，需管理令牌）"),
 ("GET /v1/hw/scan","硬件内核扫描（宿主能力，需管理令牌+限频）"),
 ("GET /v1/hw/events","硬件事件流（宿主能力，需管理令牌+限频）"),
 ("POST /v1/hw/events","硬件事件提交（宿主能力，需管理令牌+限频）"),
]
# 找 FLOW_OPS 数组真正的收尾 '];'
i=s.index("const FLOW_OPS = [")
j=s.index("];", i)
head=s[:j].rstrip()
if not head.endswith(","): head=head+","
block="\n".join("  { ep: '%s', why: '%s' }," % (ep,why) for ep,why in additions)
s2=head+"\n"+block+"\n"+s[j:]
open(p,"w",encoding="utf-8").write(s2)
print("  ✓ 已加入 %d 个端点到 FLOW_OPS" % len(additions))
PYEOF
echo
node -e "require('$P')" 2>&1 && echo "  语法 OK"
echo
cd /opt/bingdashan
python3 scripts/ops/ledger_audit.py 2>&1 | grep -iE "门禁|通过|未通过|钱漏|真漏网|墙覆盖|高风险" | head
echo "  audit exit: ${PIPESTATUS[0]}"
