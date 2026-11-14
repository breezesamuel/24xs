#!/usr/bin/env bash
# 定位 contact_email_map 实际写哪了 + 为什么 winback 读不到
echo "=== 全盘找 contact_email_map.json (CN) ==="
find /var/lib/bingdashan-cn /www/wwwroot/tools-cn.highkingflower.com /tmp /opt -name "contact_email_map.json" 2>/dev/null | head
echo ""
echo "=== track.js 的 fileStore() 实际返回啥 (CN 进程视角) ==="
grep -E "^FILE_STORE_DIR=" /etc/bingdashan-cn.env
echo "--- 进程 1644440 的 env (实际加载的 FILE_STORE_DIR) ---"
cat /proc/1644440/environ 2>/dev/null | tr '\0' '\n' | grep -iE "FILE_STORE_DIR|KV_REST|UPSTASH" | head
echo ""
echo "=== 直接调 track.js 看 kset 写到哪 (node 内联, 带 CN env) ==="
cd /www/wwwroot/tools-cn.highkingflower.com
set -a; source /etc/bingdashan-cn.env; set +a
node -e '
(async()=>{
  const t=require("./api/track.js");
  // 直接调 record 的 email 分支
  const r = await t({method:"POST",url:"/api/contact"}, {writeHead(){},end(){}}, {e:"register_email", r:"aodm", email:"aodm_dbg@example.com"});
  console.log("record email 结果:", JSON.stringify(r));
  console.log("FILE_STORE_DIR =", process.env.FILE_STORE_DIR);
  const fs=require("node:fs");
  const f=process.env.FILE_STORE_DIR+"/contact_email_map.json";
  console.log("文件存在:", fs.existsSync(f));
  if(fs.existsSync(f)) console.log("内容:", fs.readFileSync(f,"utf8"));
})().catch(e=>console.log("ERR",e.message));
'
echo done
