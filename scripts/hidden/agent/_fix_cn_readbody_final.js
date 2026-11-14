#!/usr/bin/env node
// 根治 CN site_cn_server.mjs readBody 死锁/丢 body:
// 换成可靠的事件版 (data/end/error + 30s 兜底), 删掉 stream 版的 readable===false + read() 竞态
const fs = require('fs');
const P = '/www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs';
let src = fs.readFileSync(P, 'utf8');
fs.copyFileSync(P, P + '.bak_rbfixed_' + Date.now());

const start = src.indexOf('function readBody(req)');
if (start < 0) { console.log('未找到 readBody'); process.exit(1); }
// 找配对结尾 }
let i = start, depth = 0, end = -1;
for (; i < src.length; i++) {
  const c = src[i];
  if (c === '{') depth++;
  else if (c === '}') { depth--; if (depth === 0) { end = i; break; } }
}
if (end < 0) { console.log('未找到 readBody 结尾'); process.exit(1); }

const newRB = `function readBody(req) {
  return new Promise((resolve) => {
    let raw = "";
    let settled = false;
    const timer = setTimeout(() => { finish(); }, 30000); // 兜底: 异常流 30s 强制结束
    function finish() {
      if (settled) return; settled = true;
      clearTimeout(timer);
      try {
        req.removeListener("data", onData);
        req.removeListener("end", onEnd);
        req.removeListener("error", onErr);
      } catch (e) {}
      let body = {};
      const ct = String((req.headers && req.headers["content-type"]) || "");
      if (raw) {
        if (ct.includes("application/json")) { try { body = JSON.parse(raw); } catch (e) { body = { _raw: raw }; } }
        else if (ct.includes("application/x-www-form-urlencoded")) { body = Object.fromEntries(new URLSearchParams(raw)); }
        else { try { body = JSON.parse(raw); } catch (e) { body = { _raw: raw }; } }
      }
      resolve(body);
    }
    function onData(c) { if (!settled) { raw += c; if (raw.length > 2e6) { try { req.destroy(); } catch (e) {} } } }
    function onEnd() { finish(); }
    function onErr() { finish(); }
    req.on("data", onData);
    req.on("end", onEnd);
    req.on("error", onErr);
    // 不 pause/resume, 不 readable===false 短路 (那会与 nginx 缓冲的 body 竞态 -> 丢 body / 死锁)。
    // 空 body 的 GET/HEAD/CL:0 由调用处 body = (POST? readBody : {}) 守卫; 这里正常等 data/end。
    // 若连接立即关闭且无 body, 'end' 会触发; 若半开, 30s 兜底。
  });
}`;

src = src.slice(0, start) + newRB + src.slice(end + 1);
fs.writeFileSync(P, src);
console.log('CN readBody 已替换为可靠事件版 (删 stream 竞态)');
