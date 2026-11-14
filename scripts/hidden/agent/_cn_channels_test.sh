#!/usr/bin/env bash
# 验证 CN channels.html (引流发布页) + 新 ?a=post 端点 + 完整回路
echo "=== 1. channels.html 是否可访问 (HTTP) ==="
curl -sk "https://tools-cn.highkingflower.com/channels.html" -o /tmp/_ch.html -w "HTTP %{http_code} size=%{size_download}\n" --max-time 25
echo "  含赚钱回路?", grep -c "赚钱回路" /tmp/_ch.html 2>/dev/null
echo "  含 /api/track 引流?", grep -c "/api/track" /tmp/_ch.html 2>/dev/null
echo "=== 2. ?a=post (写作投稿, 服务端质量门禁) ==="
# 短内容 -> 拒
curl -sk "https://tools-cn.highkingflower.com/api/writerewards" --max-time 25 \
  -H "Content-Type: application/json" -X POST \
  -d '{"ref":"POSTTEST","action":"post","content":"太短"}' | head -c 100; echo " (短内容应拒)"
# 正常长内容 -> 给币
LONG="这是一篇测试文章, 关于双足机器人拉格朗日动力学与增益调度 LQR 控制器。讨论倒立摆平衡的线性化工作点、闭环极点配置、支撑相摆动相切换的 ZMP 轨迹规划, 以及数值稳定性验证方法与工程实现细节。"
curl -sk "https://tools-cn.highkingflower.com/api/writerewards" --max-time 25 \
  -H "Content-Type: application/json" -X POST \
  -d "{\"ref\":\"POSTTEST\",\"action\":\"post\",\"content\":\"$LONG\",\"title\":\"t\"}" | head -c 140; echo " (正常长文应 ok + tokens)"
echo "=== 3. 清理测试数据 ==="
rm -f /var/lib/bingdashan-cn/writerewards/wr:POSTTEST.json /var/lib/bingdashan-cn/bounty/by:POSTTEST.json 2>/dev/null
echo "  已清理"
echo "=== done ==="
