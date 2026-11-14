#!/usr/bin/env python3
"""CN 端: 直接调 cashback.record (in-process) 写一条, 再 ?a=summary 读回, 验证文件存储 + 对账全链路"""
import subprocess, urllib.request, ssl, json, os
def ssh(cmd, t=60):
    r = subprocess.run(["ssh","-o","ConnectTimeout=25","aliyun",cmd], capture_output=True, text=True, timeout=t)
    return r.stdout.strip(), r.stderr.strip()
# 1. 在 CN 写一个临时 node 脚本调 cashback.record (模拟支付成功后记账)
testjs = r"""
const path = require('path');
// CN 运行环境: 从 ops/site_cn_server.mjs 的 env 加载
require('dotenv').config({ path: '/etc/bingdashan-cn.env' });
const cb = require('/www/wwwroot/tools-cn.highkingflower.com/lib/cashback.js');
(async () => {
  // 写两条 (一条模拟, 一条真实形态) - 用临时 ref
  const r1 = await cb.record('CBKTEST1', { out_trade_no: 'BDS_CBKTEST1_trial_1', amount: 100, plan: 'pro', kind: 'sub', merchant: 'jd' });
  const r2 = await cb.record('CBKTEST1', { out_trade_no: 'BDS_CBKTEST1_trial_1', amount: 100, plan: 'pro' }); // 幂等, 应 duplicate
  const r3 = await cb.record('CBKTEST1', { out_trade_no: 'BDS_CBKTEST1_pro_2', amount: 200, plan: 'pro', merchant: 'taobao' });
  console.log(JSON.stringify({ r1: r1.ok, r1_cb: r1.entry && r1.entry.cashback, dup: r2.duplicate, r3_cb: r3.entry && r3.entry.cashback }));
  // 读回 summary
  const sum = await cb.summarize('CBKTEST1', await (async()=>{ // 重新 load
    const raw = await cb.load('CBKTEST1'); return raw;
  })());
  console.log(JSON.stringify({ summary: sum }));
})();
"""
# 写到 CN
ssh("mkdir -p /tmp/_cbk")
ssh(f"cat > /tmp/_cbk_test.js <<'PYEOF'\n{testjs}\nPYEOF\n")
# 需 dotenv; 若 CN 无 dotenv, 用直接 source env 的写法。先试, 无 dotenv 则 fallback
out,_ = ssh("cd /www/wwwroot/tools-cn.highkingflower.com && node /tmp/_cbk_test.js 2>&1", t=40)
print("=== CN in-process cashback.record 测试 ===")
print(out[:600])
print()
# 2. 通过 HTTP ?a=summary 读回 (验证存储持久化 + 端点)
ctx = ssl.create_default_context()
def call(url):
    try:
        r = urllib.request.urlopen(url, timeout=30, context=ctx); return r.status, r.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()
s,b = call("https://tools-cn.highkingflower.com/api/cashback?action=summary&ref=CBKTEST1")
print("=== HTTP ?a=summary&ref=CBKTEST1 ===")
print(s, b[:300])
j = json.loads(b)
print()
print("判定:")
print("  文件存储可写?", "store" in b and "file" in b or "ok" in b)
print("  返现金额 (100元*5%=5, 200*5%=10, 总=15):", j.get("cashback_total"))
print("  can_settle (>=10门槛且有余)?", j.get("can_settle"))
