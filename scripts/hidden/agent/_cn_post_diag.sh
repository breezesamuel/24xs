#!/usr/bin/env bash
# 诊断: CN ?a=post 的 body 是否到达 handler (验证 §12.3 body bug 是否仍阻写作渠道)
echo "=== 直连 node (绕 nginx) 测 ?a=post ==="
LONG="这是一篇足够长的测试文章, 关于双足机器人拉格朗日动力学建模与增益调度 LQR 控制器的工程设计, 详细讨论了倒立摆平衡的线性化工作点选择、闭环极点配置方法、支撑相与摆动相切换时的 ZMP 轨迹规划实现, 以及数值稳定性验证的多种手段和实际工程落地细节, 全文内容充实。"
# 直连 127.0.0.1:8794 (node)
curl -s "http://127.0.0.1:8794/api/writerewards" --max-time 25 \
  -H "Content-Type: application/json" -X POST \
  -d "{\"ref\":\"DIRECTTEST\",\"action\":\"post\",\"content\":\"$LONG\"}" -o /tmp/_direct.json -w "HTTP %{http_code}\n"
echo "  直连结果:"; cat /tmp/_direct.json | head -c 200; echo
echo "=== 经 nginx 公网 (对照) ==="
curl -sk "https://tools-cn.highkingflower.com/api/writerewards" --max-time 25 \
  -H "Content-Type: application/json" -X POST \
  -d "{\"ref\":\"NGXTEST\",\"action\":\"post\",\"content\":\"$LONG\"}" -o /tmp/_ngx.json -w "HTTP %{http_code}\n"
echo "  nginx 结果:"; cat /tmp/_ngx.json | head -c 200; echo
echo "=== 判定 ==="
echo "  若 直连=ok(tokens) 但 nginx=空/拒绝 -> §12.3 body bug 仍阻写作渠道经公网提交 (需先根治 CN nginx body)"
rm -f /var/lib/bingdashan-cn/writerewards/wr:DIRECTTEST.json /var/lib/bingdashan-cn/writerewards/wr:NGXTEST.json 2>/dev/null
echo "已清理"
