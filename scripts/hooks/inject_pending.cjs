#!/usr/bin/env node
/**
 * inject_pending.mjs - patch all Arcade game pages with server-side pending-order banner.
 * Idempotent (marker guarded). Non-destructive: only adds, never touches billing/heartbeat.
 * Pure ASCII source; all Chinese injected via \uXXXX escapes.
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ARCADE = process.argv[2]
  ? path.resolve(process.argv[2])
  : (fs.existsSync(path.resolve(__dirname, '../../site/arcade'))
      ? path.resolve(__dirname, '../../site/arcade')
      : 'C:/bingdashan/site/arcade');
const MARK = 'PENDBANNER_V1';

const BEACON_OLD = "if(typeof j.balanceSeconds==='number'&&j.balanceSeconds>bal()){setnum('bal',j.balanceSeconds);hud();}}";
const BEACON_NEW = "if(typeof j.balanceSeconds==='number'&&j.balanceSeconds>bal()){setnum('bal',j.balanceSeconds);hud();}\n  " + MARK + "&&pendShow(j.pending);}}";

const FUNC_OLD = "function modal(html){var m=d.getElementById('modal');";

const FUNC_NEW = [
  '/* ' + MARK + ' server-side pending-order banner */',
  'function pendMin(p){return ({t30:30,t60:60,t300:300,t1000:1000,m10:600,m30:1800,m100:6000})[p.plan]||0;}',
  'function pendOpen(p){try{AR.buy(p.plan);}catch(e){}try{localStorage.setItem("bds_pending_"+slug(),JSON.stringify({plan:p.plan,out:p.out_trade_no,ts:Date.now()}));}catch(e){}}',
  'function pendGo(plan,out){try{var q="?plan="+encodeURIComponent(plan)+"&out_trade_no="+encodeURIComponent(out)+"&slug="+encodeURIComponent(slug())+"&ref="+encodeURIComponent(me());location.href="/api/pay"+q;}catch(e){}}',
  'function pendShow(p){if(!p||!p.plan)return;try{var el=document.getElementById("pendtip");',
  'if(!el){el=document.createElement("div");el.id="pendtip";',
  'el.style.cssText="position:fixed;left:0;right:0;bottom:0;background:#fef3c7;border-top:2px solid #f59e0b;color:#78350f;padding:10px 14px;text-align:center;font-size:14px;z-index:40;cursor:pointer";',
  'el.onclick=function(){pendOpen(p);};',
  'document.body.appendChild(el);}',
  'var mins=pendMin(p);',
  'el.textContent="\\u60a8\\u8fd8\\u6709\\u4e00\\u7b14\\u672a\\u5b8c\\u6210\\u7684\\u8ba2\\u5355\\uff08\\u00a5"+p.amount+"\\uff09\\u2014\\u70b9\\u51fb\\u7ee7\\u7eed\\u652f\\u4ed8"+(mins?" \\xb7 "+mins+" \\u5206\\u949f":"");',
  '}catch(e){}}',
  'window.pendShow=pendShow;',
  'function modal(html){var m=d.getElementById("modal");'
].join('\n');

function walk(dir){
  if(!fs.existsSync(dir)) return;
  for(const f of fs.readdirSync(dir)){
    const p = path.join(dir, f);
    const st = fs.statSync(p);
    if(st.isDirectory()){ walk(p); continue; }
    if(f !== 'index.html') continue;
    if(!p.includes('arcade')) continue;
    patch(p);
  }
}

let patched = 0, skipped = 0, failed = 0;

function patch(file){
  try{
    let html = fs.readFileSync(file, 'utf8');
    if(html.indexOf(MARK) >= 0){ skipped++; return; }
    let changed = false;
    if(html.indexOf(BEACON_OLD) >= 0){
      html = html.replace(BEACON_OLD, BEACON_NEW);
      changed = true;
    }
    if(html.indexOf(FUNC_OLD) >= 0){
      html = html.replace(FUNC_OLD, FUNC_NEW);
      changed = true;
    }
    if(changed){ fs.writeFileSync(file, html, 'utf8'); patched++; }
    else skipped++;
  }catch(e){ failed++; console.log('FAIL ' + file + ' ' + e.message); }
}

walk(ARCADE);
console.log('[inject_pending] patched=' + patched + ' skipped=' + skipped + ' failed=' + failed);
