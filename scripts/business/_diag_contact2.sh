#!/usr/bin/env bash
# 诊断 /api/contact HTTP 路径为什么不落盘 (callHandler 传字段 + track.js 收字段)
echo "=== 1. site_cn_server.mjs 的 callHandler 怎么把 body 传给 handler ==="
grep -nE "function callHandler|callHandler\(|data\.path|\.email|Object.assign.*data|query\[" /www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs | head -15
echo ""
echo "=== 2. 看 callHandler 定义体 ==="
sed -n "/function callHandler/,/^}/p" /www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs | head -25
echo ""
echo "=== 3. track.js email 分支实际判断的字段 (确认读 p.email 还是 p.em) ==="
grep -nE "register_email|persist_email|p\.email|p\.em|p\.r |contact_email_map" /www/wwwroot/tools-cn.highkingflower.com/api/track.js | head
echo ""
echo "=== 4. 直接模拟 callHandler 传参, 看 track.js 收到啥 ==="
cd /www/wwwroot/tools-cn.highkingflower.com
set -a; source /etc/bingdashan-cn.env; set +a
node -e '
(async()=>{
  const t=require("./api/track.js");
  // 模拟 callHandler: data = {query合并}, 看它 email 分支读哪个字段
  const r1=await t({method:"POST"}, {writeHead(){},end(){}}, {e:"register_email", r:"GET", email:"x@y.co"});
  console.log("  传 email 字段 ->", JSON.stringify(r1||{}));
})().catch(e=>console.log("ERR",e.message));
'
echo done
