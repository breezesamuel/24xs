#!/usr/bin/env node
// CN site_cn_server.mjs: shimReq 设 _bdsBodyInUrl=true (告知 alipay.js 别重读流, body 已在 URL)
const fs = require('fs');
const P = '/www/wwwroot/tools-cn.highkingflower.com/ops/site_cn_server.mjs';
let src = fs.readFileSync(P, 'utf8');
fs.copyFileSync(P, P + '.bak_shimflag_' + Date.now());
const anchor = 'shimReq.url = u2.pathname + u2.search;';
if (src.includes(anchor)) {
  if (!src.includes('_bdsBodyInUrl')) {
    src = src.replace(anchor, anchor + '\n      shimReq._bdsBodyInUrl = true; // body 已 merge 进 URL, alipay.js 勿重读流 (防死锁/hang)');
    fs.writeFileSync(P, src);
    console.log('CN shimReq._bdsBodyInUrl=true 已加');
  } else {
    console.log('已存在 _bdsBodyInUrl, 跳过');
  }
} else {
  console.log('未找到 shimReq.url anchor, 跳过');
}
