#!/usr/bin/env bash
# 最终全验证: 引流页 + 4 渠道 + body 修复 (CN 生产)
echo "=== 引流页 /channels.html ==="
curl -sk "https://tools-cn.highkingflower.com/channels.html" -o /dev/null -w "  HTTP %{http_code} size=%{size_download}\n" --max-time 25
echo "=== 4 渠道端点 ==="
for e in "bounty?action=tasks" "cashback?action=rate" "writerewards?action=rate" "config"; do
  printf "  %s: " "$e"; curl -sk "https://tools-cn.highkingflower.com/api/$e" --max-time 20 -o /dev/null -w "HTTP %{http_code}\n"
done
echo "=== body 修复确认 (POST /api/pay, 应 0.0Xs + ref 进 out_trade_no) ==="
curl -sk "https://tools-cn.highkingflower.com/api/pay" --max-time 25 -H "Content-Type: application/x-www-form-urlencoded" --data "plan=trial&ref=FINALCHECK&amount=1" -o /tmp/_fc.html -w "  HTTP %{http_code} time=%{time_total}s\n" 2>&1
grep -oE "BDS_FINALCHECK_[a-z_]+" /tmp/_fc.html 2>/dev/null | head -1
echo "=== 写作 ?a=post (经公网, 应 ok+tokens) ==="
LONG="这是足够长的测试文章, 讨论双足机器人拉格朗日动力学建模与增益调度 LQR 控制器设计, 涵盖倒立摆平衡线性化工作点选择、闭环极点配置、支撑相与摆动相切换时的 ZMP 轨迹规划与数值稳定性验证方法, 以及工程落地细节, 全文充实。"
curl -sk "https://tools-cn.highkingflower.com/api/writerewards" --max-time 25 -H "Content-Type: application/json" -X POST \
  -d "{\"ref\":\"FINALWR\",\"action\":\"post\",\"content\":\"$LONG\",\"title\":\"t\"}" -o /tmp/_fw.json -w "  HTTP %{http_code} time=%{time_total}s\n" 2>&1
head -c 120 /tmp/_fw.json 2>/dev/null; echo
rm -f /var/lib/bingdashan-cn/writerewards/wr:FINALWR.json 2>/dev/null
echo "=== done (测试数据已清理) ==="
