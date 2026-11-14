#!/usr/bin/env node
// CN readBody 最终版: 事件版 + req.resume() (node 请求流默认 paused, 必须 resume 才发 data), 但 *不* 用 readable===false 短路
const fs = require('fs');
const P = '/www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs';
let src = fs.readFileSync(P, 'utf8');
fs.copyFileSync(P, P + '.bak_rbfixed2_' + Date.now());

const start = src.indexOf('function readBody(req)');
if (start < 0) { console.log('未找到 readBody'); process.exit(1); }
let i = start, depth = 0, end = -1;
for (; i < src.length; i++) {
  const c = src[i];
  if (c === '{') depth++;
  else if (c === '}') { depth--; if (depth === 0) { end = i; break; } }
}
if (end < 0) { console.log('未找到结尾'); process.exit(1); }

const newRB = `function readBody(req) {
  return new Promise((resolve) => {
    let raw = "";
    let settled = false;
    const timer = setTimeout(() => { finish(); }, 30000);
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
    // 关键: node 请求流默认 paused, 必须 resume 才会发 data 事件 (否则 POST body 永远读不到 -> 30s 超时)。
    // 不用 readable===false 短路 (那会与 nginx 缓冲的 body 竞态丢数据)。空 body 的 GET/HEAD 由调用处 (POST? readBody : {}) 守卫。
    try { req.resume(); } catch (e) {}
  });
}`;

src = src.slice(0, start) + newRB + src.slice(end + 1);
fs.writeFileSync(P, src);
console.log('CN readBody 最终版: 事件 + resume (无 readable 短路)');
