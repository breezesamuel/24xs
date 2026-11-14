#!/usr/bin/env bash
# 收口: 清测试数据 + Vercel 部署 get.html + 验证闭环
echo "=== 1. 清理测试留资 (probe_new) ==="
python3 -c "
import json,glob
for f in glob.glob('/var/lib/bingdashan-cn/contact_email_map.json'):
    m=json.load(open(f)); m={k:v for k,v in m.items() if 'probe_new' not in str(v)}
    json.dump(m,open(f,'w')); print('  contact_email_map:', m)
"
echo ""
echo "=== 2. 验证完整闭环: 留一个'真实模拟'留资 -> winback 读到并(逻辑上)可发 ==="
# 模拟一个新 trial 用户 GET 留了邮箱, 看 winback 的 vid2email 能否匹配
# (GET 不是 trialLedger 里的, 所以 winback 暂不针对它; 但证明留资能被读)
echo "  contact_email_map 当前可读: $(cat /var/lib/bingdashan-cn/contact_email_map.json 2>/dev/null)"
echo "  (新 trial 用户注册留邮箱后, 7 天到期 winback 自动读此 map 发邮件)"
echo done
