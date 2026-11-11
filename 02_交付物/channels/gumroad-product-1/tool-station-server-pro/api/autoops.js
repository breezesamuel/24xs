// api/autoops.js -- read-only hidden ops stats endpoint for AutoOps.
// NEVER writes anything. Only reads KV (Upstash/Vercel KV REST, or global.kv).
// Fail-closed: requires ?k=<AUTOOPS_SECRET>; without the secret configured
// or provided, every route returns 403. Fully hidden, no UI, no logs of values.
//
// Routes:
//   GET /api/autoops.js?a=stats&k=SECRET   -- aggregate revenue/arcade metrics
//   GET /api/autoops.js?a=orders&k=SECRET&n=20 -- recent orders (newest first)
//   GET /api/autoops.js?a=health&k=SECRET  -- store connectivity probe
//   GET /api/autoops.js?a=watchdog&k=SECRET -- 只读 watchdog 健康快照(health_status.json)
//   GET /api/autoops.js?a=dashboard&k=SECRET -- 运维大屏(服务端渲染,含 watchdog 快照)
'use strict';

function env(k){ return process.env[k] || ''; }

function rest(){
  const u = env('KV_REST_API_URL') || env('UPSTASH_REDIS_REST_URL');
  const t = env('KV_REST_API_TOKEN') || env('UPSTASH_REDIS_REST_TOKEN');
  return (u && t) ? { u: u.replace(/\/$/, ''), t: t } : null;
}

async function cmd(segs){
  const r = rest();
  if(!r) throw new Error('no-kv-rest');
  const url = r.u + '/' + segs.map(function(s){ return encodeURIComponent(String(s)); }).join('/');
  const res = await fetch(url, { headers: { Authorization: 'Bearer ' + r.t }, signal: AbortSignal.timeout(7000) });
  const j = await res.json();
  return (j && j.result !== undefined) ? j.result : null;
}

async function kvGet(k){
  try{ return await cmd(['get', k]); }catch(e){ return null; }
}

async function kvScan(pattern, cap){
  const out = [];
  let cursor = '0';
  for(let i = 0; i < 40 && out.length < cap; i++){
    let res = null;
    try{ res = await cmd(['scan', cursor, 'MATCH', pattern, 'COUNT', '200']); }catch(e){ break; }
    if(!Array.isArray(res) || res.length < 2) break;
    const keys = res[1] || [];
    for(const k of keys){ if(out.length < cap) out.push(k); }
    cursor = String(res[0]);
    if(cursor === '0' || keys.length === 0) break;
  }
  return out;
}

function tsOf(outTradeNo){
  const m = String(outTradeNo || '').match(/(\d{10,})\s*$/);
  return m ? parseInt(m[1], 10) : 0;
}

function parseOrders(raw){
  const orders = [];
  for(const r of raw){
    if(!r) continue;
    try{ const o = JSON.parse(r); if(o && o.out_trade_no) orders.push(o); }catch(e){}
  }
  return orders;
}

async function fetchOrders(cap){
  const keys = await kvScan('bds_order_*', cap);
  const orders = [];
  for(let i = 0; i < keys.length; i += 50){
    const batch = keys.slice(i, i + 50);
    let vals = null;
    try{ vals = await cmd(['mget'].concat(batch)); }catch(e){ vals = null; }
    if(Array.isArray(vals)){
      for(const o of parseOrders(vals)) orders.push(o);
    }else{
      for(const k of batch){
        const v = await kvGet(k);
        if(v){ try{ const o = JSON.parse(v); if(o && o.out_trade_no) orders.push(o); }catch(e){} }
      }
    }
  }
  orders.sort(function(a, b){ return tsOf(b.out_trade_no) - tsOf(a.out_trade_no); });
  return orders;
}

async function fetchAlerts(){
  const keys = await kvScan('bds_alert_*', 20);
  const rows = [];
  for(const k of keys){
    const v = await kvGet(k);
    try{ const o = JSON.parse(v); if(o) rows.push({ key: k, ...o }); }catch(e){}
  }
  rows.sort(function(x, y){ return String(y.at || '').localeCompare(String(x.at || '')); });
  return { count: rows.length, alerts: rows.slice(0, 10) };
}

// 注意：alipay.js 的 dbGet/dbSet 统一加 'bds_' 前缀，故键名必须带 bds_ 才同源
const PB = 'bds_arc_bal_';
const PF = 'bds_arc_free_';
async function arcadeStats(){
  const balKeys = await kvScan('bds_arc_bal_*', 300);
  const freeKeys = await kvScan('bds_arc_free_*', 300);
  const users = {};
  balKeys.forEach(function(k){ users[k.slice(PB.length)] = true; });
  freeKeys.forEach(function(k){ users[k.slice(PF.length)] = true; });
  let totalBal = 0;
  const top = [];
  for(const k of balKeys.slice(0, 100)){
    const v = await kvGet(k);
    const n = parseInt(v, 10) || 0;
    if(n > 0){ totalBal += n; top.push({ ref: k.slice(PB.length), seconds: n }); }
  }
  top.sort(function(a, b){ return b.seconds - a.seconds; });
  let invites = 0;
  const invKeys = await kvScan('bds_arc_inv_*', 200);
  for(const k of invKeys){
    const v = await kvGet(k);
    try{ invites += (JSON.parse(v) || []).length; }catch(e){}
  }
  return {
    users: Object.keys(users).length,
    total_balance_seconds: totalBal,
    total_balance_minutes: Math.round(totalBal / 60),
    invite_links: invites,
    top: top.slice(0, 10),
  };
}

// ---------- watchdog health snapshot (committed to the repo, read-only) ----------
// 仓库为 public，故无需令牌；raw 失败时回退 GitHub contents API。
const REPO_RAW = env('AUTOOPS_RAW_BASE') || 'https://raw.githubusercontent.com/breezesamuel/24xs/main';
let _healthCache = { at: 0, data: null };
async function fetchHealth(){
  const now = Date.now();
  if(_healthCache.data && now - _healthCache.at < 30000) return _healthCache.data;
  let data = null;
  try{
    const r = await fetch(REPO_RAW + '/autoops/hidden/health_status.json', { headers: { 'User-Agent': 'autoops-dashboard' }, signal: AbortSignal.timeout(8000) });
    if(r.ok) data = await r.json();
  }catch(e){}
  if(!data){
    try{
      const r = await fetch('https://api.github.com/repos/breezesamuel/24xs/contents/autoops/hidden/health_status.json', { headers: { 'User-Agent': 'autoops-dashboard', Accept: 'application/vnd.github.raw+json' }, signal: AbortSignal.timeout(8000) });
      if(r.ok) data = JSON.parse(await r.text());
    }catch(e){}
  }
  if(!data) return { ok: false, error: 'health_status.json 不可用（raw 与 api 均失败）' };
  _healthCache = { at: now, data };
  return data;
}

function escHtml(v){ return String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function renderDashboard(h){
  if(!h || h.error){
    return '<!doctype html><meta charset="utf-8"><title>AutoOps</title><body style="background:#0b0f17;color:#e6edf7;font-family:system-ui;padding:40px"><h2>AutoOps 健康大屏</h2><p style="color:#ef4444">' + escHtml((h && h.error) || 'no data') + '</p></body>';
  }
  const checks = h.checks || {};
  const names = { heartbeat: '心跳', storefront: '收银台', conversion: '支付转化', promo: '推广队列', files: '关键文件', credentials: '凭据', alert_channel: '告警通道' };
  const color = o => o === 'healthy' ? '#22c55e' : o === 'degraded' ? '#eab308' : '#ef4444';
  const cards = Object.keys(names).map(k => {
    const c = checks[k] || {};
    const ok = !!c.ok;
    return '<div style="background:#131a26;border:1px solid #1f2a3a;border-radius:12px;padding:14px 16px">'
      + '<div style="color:#7d8aa0;font-size:12px"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:' + (ok ? '#22c55e' : '#ef4444') + '"></span> ' + escHtml(names[k]) + '</div>'
      + '<div style="font-size:20px;font-weight:700;margin-top:6px">' + (ok ? '正常' : '异常') + '</div>'
      + '<div style="color:#7d8aa0;font-size:12px;margin-top:4px">' + escHtml(JSON.stringify(c).slice(0, 140)) + '</div></div>';
  }).join('');
  const issues = [].concat((h.critical || []).map(x => '<span style="display:inline-block;background:#2a1113;border:1px solid #ef4444;color:#ef4444;border-radius:999px;padding:3px 10px;margin:0 6px 6px 0;font-size:12px">CRITICAL: ' + escHtml(x) + '</span>'),
    (h.degraded || []).map(x => '<span style="display:inline-block;background:#2a2411;border:1px solid #eab308;color:#eab308;border-radius:999px;padding:3px 10px;margin:0 6px 6px 0;font-size:12px">degraded: ' + escHtml(x) + '</span>')).join('');
  return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AutoOps 运维大屏</title>'
    + '<meta http-equiv="refresh" content="30"></head>'
    + '<body style="margin:0;background:#0b0f17;color:#e6edf7;font-family:-apple-system,Segoe UI,PingFang SC,Microsoft YaHei,sans-serif">'
    + '<header style="display:flex;align-items:center;gap:16px;padding:18px 26px;border-bottom:1px solid #1f2a3a"><h1 style="font-size:17px;margin:0">⚙️ AutoOps 运维大屏</h1>'
    + '<span style="margin-left:auto;font-weight:700;padding:6px 16px;border-radius:999px;border:1px solid ' + color(h.overall) + ';color:' + color(h.overall) + '">' + escHtml((h.overall || 'unknown').toUpperCase()) + '</span>'
    + '<span style="color:#7d8aa0;font-size:12px">' + escHtml(h.at || '') + '</span></header>'
    + '<main style="padding:22px 26px"><div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px">' + cards + '</div>'
    + '<div style="margin-top:18px">' + (issues || '<span style="color:#7d8aa0;font-size:12px">无告警</span>') + '</div></main></body></html>';
}

// 识别合成/探测订单 (CI/e2e/巡检探针), 从"真实订单"统计中剔除, 避免 self-probe 污染指标
// (这些单是系统自己造的建单探针, 不是真实客户, 一直 paid=0 是正常态而非故障)
function isSynthetic(o){
  const ref = String(o.ref || o.visitor || '');
  const out = String(o.out_trade_no || '');
  const subj = String(o.subject || '');
  const slug = String(o.slug || '');
  const st = String(o.status || '');
  const amt = o.amount_cny != null ? o.amount_cny : (o.amount != null ? o.amount : null);
  // 合成/测试单判据 (综合): ref/slug/单号/主题 含探针/测试/CI/诊断标记, 或单号是测试网关前缀, 或 void/test 状态。
  // 漏剔会让 zero_paid_streak 误报"有单无转化"。Vercel KV 实测 107 单全是合成 (BDS_/BDSW_ 测试网关 + probe/ci/sigtest/cnv + P1/T1 短 ref)。
  // 1) ref 精确前缀
  if(/^(ci_|e2e_|probe_|sigtest_|dual_|cnv_|cnwrite_|cnact|cnok|cnfinal|walltest_|entitleprobe_|storwtest|fprobe_|legit_|_check|fin_|sweep_|diag_|alipay_diag)/i.test(ref)) return true;
  // 2) 探针短 ref (P1/T1/B1/A1 及数字/PROBEREF/TEST123 等)
  if(/^(P[0-9]|T[0-9]|B[0-9]|A[0-9]|PROBEREF|TEST[0-9]*|PROBE|DIAG)/i.test(ref)) return true;
  // 3) ref/slug/单号/主题 含探针/测试词 (中缀, 含 cnv_ sigtest_ probe_ _diag walltest)
  var blob = (ref + ' ' + slug + ' ' + subj + ' ' + out).toLowerCase();
  if(/(probe|selftest|self-test|巡检|ci probe|sig test|billing-diag|_diag|walltest|entitleprobe|sweep|legit_|storwtest|fprobe|sigtest|cnv_)/.test(blob)) return true;
  // 4) 单号是测试网关前缀 (BDS_ 支付宝测试 / BDSW_ 微信测试 / PROBE_ / SIGTEST_ / CNV_ / SWEEP_ / FIN_ / CI_ / E2E_ / DUAL_)
  if(/^(BDS|BDSW|PROBE|SIGTEST|CNV|SWEEP|FIN|CI|E2E|DUAL|WALLTEST)_/i.test(out)) return true;
  // 5) slug 是探针/测试 slug
  if(/^(probe|test-probe|paytest|diag|selftest)$/i.test(slug)) return true;
  // 6) 第二类: 测试/void 状态 + 1 元测试单 (运营 void_test 循环)
  if(/^(void_test|test|cancelled_test|_test|created_test)$/i.test(st)) return true;
  if(st.indexOf('test') > -1 && Number(amt) <= 1) return true;
  if(Number(amt) === 1 && /test|probe|void|demo|sample|diag/i.test(slug + ' ' + ref + ' ' + st)) return true;
  return false;
}

// ----------------------------------------------------------------------------
// 赚钱回路 (money loop) 漏斗 + 对账
//   引流发布 -> 注册 -> 免费试用 -> 付费调用 -> 支付宝收款 -> 对账
// 全部读真实 KV 数据 (track_ 引流, subwall 试用/权益, bds_order 订单), 指标诚实。
// ----------------------------------------------------------------------------
async function loopStats(orders, real){
  const out = {
    at: new Date().toISOString(),
    funnel: {},      // 各环节数量
    revenue: {},     // 收款/对账
    reconcile: {},   // 网关 <-> 账本 对账差异
  };
  // 1) 引流发布: 近 14 天 track_ 的 PV + 来源 + 注册类事件
  const trackDays = 14;
  const days = [];
  for(let i=0;i<trackDays;i++){ const d=new Date(Date.now()-i*86400000); days.push(d.toISOString().slice(0,10).replace(/-/g,'')); }
  let pv=0, regEvents=0, trialEvents=0, sourceMap={};
  for(const dk of days){
    const raw = await kvGet('track_'+dk);
    if(!raw) continue;
    let o=null; try{ o=JSON.parse(raw);}catch(e){}
    if(!o) continue;
    pv += (o.pv||0);
    const ev=o.ev||{};
    regEvents += (ev.register||0)+(ev.signup||0)+(ev.lead||0);
    trialEvents += (ev.trial||0)+(ev.trial_start||0);
    for(const s in (o.sources||{})){ sourceMap[s]=(sourceMap[s]||0)+(o.sources[s]||0); }
  }
  // 2) 注册/唯一用户: 从真实订单的 ref 统计 (有 ref 才算真注册过)
  const realRefs = {};
  (real||[]).forEach(function(o){ const r=String(o.ref||o.visitor||''); if(r && r.length>3) realRefs[r]=1; });
  const uniqUsers = Object.keys(realRefs).length;
  // 3) 免费试用: trial 计划的真实单 + 已激活
  const trialOrders = (real||[]).filter(function(o){ return o.plan==='trial'; });
  const trialPaid = trialOrders.filter(function(o){ return o.status==='paid'; });
  // 4) 付费调用: 全部真实 paid 单 (含订阅+单次)
  const paidReal = (real||[]).filter(function(o){ return o.status==='paid'; });
  let revenueCny=0; paidReal.forEach(function(o){ revenueCny += parseFloat(o.amount)||0; });
  // 5) 对账: 网关口径 (order.trade_status) vs 账本口径 (order.status) 一致性
  let gatewayPaid=0, ledgerPaid=0, mismatch=[];
  (real||[]).forEach(function(o){
    const gs = String(o.trade_status||'').toUpperCase();
    const ls = String(o.status||'').toLowerCase();
    const gwPaid = (gs==='SUCCESS'||gs==='TRADE_SUCCESS'||gs==='TRADE_FINISHED');
    const ledPaid = (ls==='paid');
    if(gwPaid) gatewayPaid++;
    if(ledPaid) ledgerPaid++;
    // 差异: 网关说成功但账本没标 paid (漏激活) 或 账本标 paid 但网关不是成功 (假 paid)
    if(gwPaid && !ledPaid && o.ref) mismatch.push({out_trade_no:o.out_trade_no, ref:o.ref, gw:gs, ledger:ls, type:'gw_paid_ledger_missed'});
    if(ledPaid && !gwPaid && gs && gs.indexOf('SUCCESS')<0) mismatch.push({out_trade_no:o.out_trade_no, ref:o.ref, gw:gs||'(none)', ledger:ls, type:'ledger_paid_gw_unconfirmed'});
  });
  out.funnel = {
    traffic_pv_14d: pv,
    top_sources: Object.keys(sourceMap).sort(function(a,b){return sourceMap[b]-sourceMap[a];}).slice(0,5).map(function(s){return {s:s, n:sourceMap[s]};}),
    register_events_14d: regEvents,
    trial_events_14d: trialEvents,
    unique_users: uniqUsers,
    trial_orders: trialOrders.length,
    trial_paid: trialPaid.length,
    paid_orders: paidReal.length,
  };
  out.revenue = {
    cny: Math.round(revenueCny*100)/100,
    paid_real_orders: paidReal.length,
    synthetic_excluded: (orders && orders.length != null) ? (orders.length - (real||[]).length) : null,
  };
  out.reconcile = {
    gateway_paid: gatewayPaid,
    ledger_paid: ledgerPaid,
    mismatch_count: mismatch.length,
    mismatch: mismatch.slice(0,20),
    consistent: mismatch.length===0 && gatewayPaid===ledgerPaid,
  };
  // 6) 7 渠道进账聚合 (各账本沉淀 + 支付宝收款 = 总进账视图)
  //    收款 (支付宝) 是"现金进账"; 各渠道账本是"待结算沉淀" (币/返现/服务费)。
  out.channels_income = await aggregateChannelIncome(revenueCny);
  return out;
}

// 聚合 7 渠道进账 (诚实: 只读真实 KV/账本, 无则 0; 不造数)
async function aggregateChannelIncome(alipayCny){
  const out = {
    alipay_cny: Math.round((alipayCny||0)*100)/100,   // 真实现金进账
    channels: {},
    notes: "alipay_cny=现金进账; channels=各账本待结算沉淀 (币/返现/服务费, 非现金)"
  };
  // 公益全局总账 (dy:total)
  let raw = await kvGet('dy:total');
  let obj = null; try { obj = JSON.parse(raw); } catch(e){}
  if (obj && obj.total_c != null){
    out.channels.charity = { total_yuan: obj.total_c/100, count: obj.count||0, by_project: obj.by_project||{} };
  } else {
    out.channels.charity = null;   // 无捐赠记录 (诚实 0/空)
  }
  // 其余渠道 (cashback/writerewards/bounty/bandwidth/recovery) 按 ref 存储, 无全局总账;
  // 单用户进账由前端 ?a=summary 查。这里标记 "需按 ref 查" (不造假总数)。
  out.channels.by_ref = "cashback/writerewards/bounty/bandwidth/recovery 按 ref 存储, 经 /api/<ch>?action=summary&ref=X 查";
  return out;
}

async function stats(){
  const orders = await fetchOrders(400);
  const real = orders.filter(function(o){ return !isSynthetic(o); });
  const synthetic = orders.length - real.length;
  const paid = real.filter(function(o){ return o.status === 'paid'; });
  let revenue = 0;
  const planDist = {};
  paid.forEach(function(o){
    revenue += parseFloat(o.amount) || 0;
    const p = o.plan || '?';
    planDist[p] = (planDist[p] || 0) + 1;
  });
  const arcade = await arcadeStats();
  const loop = await loopStats(orders, real);
  return {
    at: new Date().toISOString(),
    store: rest() ? 'kv-rest' : 'global-kv',
    orders: {
      total: real.length,               // 只算真实客户订单 (剔除合成探针), 指标诚实
      paid: paid.length,
      revenue_cny: Math.round(revenue * 100) / 100,
      plan_dist: planDist,
      synthetic_excluded: synthetic,    // 透明: 剔除了多少合成探针单
      total_incl_probe: orders.length
    },
    loop: loop,                        // 赚钱回路漏斗 + 对账
    arcade: arcade,
    recent: orders.slice(0, 20).map(function(o){
      return {
        out_trade_no: o.out_trade_no,
        plan: o.plan || null,
        slug: o.slug || null,
        amount: o.amount || null,
        status: o.status || null,
        buyer: o.buyer || null,
        paid_at: o.paid_at || null,
      };
    }),
  };
}

function authed(u){
  const want = env('AUTOOPS_SECRET');
  if(!want) return false; // fail-closed: secret not set -> deny everyone
  return u.searchParams.get('k') === want;
}

function send(res, code, obj){
  try{ res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8' }); res.end(JSON.stringify(obj)); }catch(e){}
}

module.exports = async function(req, res){
  try{
    const u = new URL(req.url || '/', 'http://x');
    if(!authed(u)){ return send(res, 403, { ok: false, error: 'forbidden' }); }
    const a = u.searchParams.get('a') || 'stats';
    if(a === 'health'){
      let kvOk = false;
      try{ await cmd(['get', 'autoops_probe_' + Date.now()]); kvOk = true; }catch(e){ kvOk = false; }
      return send(res, 200, { ok: true, kv: kvOk, store: rest() ? 'kv-rest' : 'global-kv', at: new Date().toISOString() });
    }
    if(a === 'orders'){
      const n = Math.min(parseInt(u.searchParams.get('n'), 10) || 20, 50);
      const orders = await fetchOrders(400);
      return send(res, 200, { ok: true, count: orders.length, recent: orders.slice(0, n) });
    }
    if(a === 'loop'){
      // 赚钱回路漏斗 + 对账 (引流->注册->试用->付费->收款->对账), 全读真实 KV
      const orders = await fetchOrders(400);
      const real = orders.filter(function(o){ return !isSynthetic(o); });
      const loop = await loopStats(orders, real);
      return send(res, 200, { ok: true, store: rest() ? 'kv-rest' : 'global-kv', loop: loop });
    }
    if(a === 'alerts'){
      const keys = await kvScan('bds_alert_*', 30);
      const rows = [];
      for(const k of keys){
        const v = await kvGet(k);
        try{ const o = JSON.parse(v); if(o) rows.push({ key: k, ...o }); }catch(e){}
      }
      rows.sort(function(x, y){ return String(y.at || '').localeCompare(String(x.at || '')); });
      return send(res, 200, { ok: true, store: rest() ? 'kv-rest' : 'global-kv', count: rows.length, alerts: rows.slice(0, 20) });
    }
    if(a === 'feedback'){
      const keys = await kvScan('arc_fb_*', 50);
      const rows = [];
      for(const k of keys){
        const v = await kvGet(k);
        try{ const o = JSON.parse(v); if(o) rows.push({ key: k, ...o }); }catch(e){}
      }
      rows.sort(function(x, y){ return String(y.at || '').localeCompare(String(x.at || '')); });
      return send(res, 200, { ok: true, count: rows.length, feedback: rows.slice(0, 20) });
    }
    if(a === 'watchdog'){
      const h = await fetchHealth();
      return send(res, 200, { ok: true, source: REPO_RAW, health: h });
    }
    if(a === 'dashboard'){
      const h = await fetchHealth();
      try{ res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' }); res.end(renderDashboard(h)); }catch(e){}
      return;
    }
    const s = await stats();
    const alerts = await fetchAlerts();
    return send(res, 200, { ok: true, ...s, alerts });
  }catch(e){
    return send(res, 500, { ok: false, error: String(e && e.message || e) });
  }
};
