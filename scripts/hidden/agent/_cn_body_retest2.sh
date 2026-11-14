#!/usr/bin/env bash
# 根治后重测 CN body 透传 (readBody 换事件版)
echo "=== 1. 直连 node /api/pay (应读到 ref) ==="
curl -s "http://127.0.0.1:8794/api/pay" --max-time 20 \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "plan=trial&ref=DIRECTFIX&amount=1" -o /tmp/_d.html -w "HTTP %{http_code} time=%{time_total}s\n" 2>&1
grep -oE '"out_trade_no":"[^"]+"' /tmp/_d.html 2>/dev/null | head -1
echo "=== 2. 经 nginx /api/pay (公网, 应读到 ref) ==="
curl -sk "https://tools-cn.highkingflower.com/api/pay" --max-time 25 \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "plan=trial&ref=NGXFIX&amount=1" -o /tmp/_n.html -w "HTTP %{http_code} time=%{time_total}s\n" 2>&1
grep -oE '"out_trade_no":"[^"]+"' /tmp/_n.html 2>/dev/null | head -1
echo "=== 3. 经 nginx ?a=post 写作投稿 (JSON body) ==="
LONG="这是一篇足够长的测试文章, 关于双足机器人拉格朗日动力学建模与增益调度 LQR 控制器设计, 讨论倒立摆平衡的线性化工作点、闭环极点配置、支撑相摆动相切换的 ZMP 轨迹规划与数值稳定性验证方法及工程落地细节。"
curl -sk "https://tools-cn.highkingflower.com/api/writerewards" --max-time 25 \
  -H "Content-Type: application/json" -X POST \
  -d "{\"ref\":\"POSTFIX\",\"action\":\"post\",\"content\":\"$LONG\",\"title\":\"t\"}" -o /tmp/_w.json -w "HTTP %{http_code} time=%{time_total}s\n" 2>&1
head -c 160 /tmp/_w.json 2>/dev/null; echo
echo "=== 判定 ==="
echo "  DIRECTFIX/NGXFIX 在 out_trade_no = /api/pay body 修复成功"
echo "  POSTFIX ok=true + tokens = 写作渠道经公网可用"
rm -f /var/lib/bingdashan-cn/writerewards/wr:POSTFIX.json 2>/dev/null
echo "已清理"
