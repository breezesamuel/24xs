'use strict';
// quantcompute.js - C10 合规渠道: 量化算力包 (按算力 credits 计费, 团队共享池, 高客单价)
// 借鉴竞品真实收费结构:
//   - QuantConnect: 算力节点按量 (Research/Backtest/Live 节点分档) + 席位 + 白标
//   - Lovable: credits 团队共享池 + 按成员限额 + 按用量持续计费
// 复用 C3~C9 同款存储原语 (KV/Supabase 双写 + CN 文件回退, key 前缀 qc:)
// 合规 (诚实 + fail-closed + 不造假):
//   - 服务端权威: 算力额度/消耗 由服务端算, 客户端不可伪造
//   - credits 按实际算力任务扣 (回测次数/优化组合数/纸面组合), 不造假算力
//   - 合规免责: 算力输出基于历史数据, 非投资建议, 不代表未来收益
// 变现: 币走 coinsettle / ¥走支付宝; 购买 = 充值该 ref 的算力 credits 池
// Endpoints: /api/quantcompute?action=rate|summary|run|ledger|purchase|record
//   run 需 credits (未购 -> 402 need_payment); purchase/record 需 admin secret
const PRICE_YUAN = (function () { var v = parseFloat(process.env.QC_PRICE_YUAN); return (isFinite(v) && v > 0) ? v : 199; })();
const PRICE_COIN = (function () { var v = parseFloat(process.env.QC_PRICE_COIN); return (isFinite(v) && v > 0) ? v : 2000; })();
const CREDITS_PER_PACK = (function () { var v = parseInt(process.env.QC_CREDITS_PER_PACK); return (isFinite(v) && v > 0) ? v : 20; })();
const ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
function fileStore() { try { var d = process.env.FILE_STORE_DIR; return (d && String(d).trim()) ? String(d).trim() : null; } catch (e) { return null; } }
function qcFilePath(key) { var dir = fileStore(); if (!dir) return null; var safe = String(key).replace(/[^A-Za-z0-9_.:-]/g, '_'); try { var p = require('path'); return p.join(dir, 'quantcompute', safe + '.json'); } catch (e) { return null; } }
async function qcFileGet(key) { var p = qcFilePath(key); if (!p) return null; try { return await require('node:fs/promises').readFile(p, 'utf8'); } catch (e) { return null; } }
async function qcFileSet(key, val) { var p = qcFilePath(key); if (!p) return false; try { var fs = require('node:fs/promises'); var P = require('path'); await fs.mkdir(P.dirname(p), { recursive: true }); await fs.writeFile(p, val, 'utf8'); return true; } catch (e) { return false; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/quantcompute_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } } if (fileStore()) { var f = await qcFileGet(k); if (f !== null && f !== undefined) return f; } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/quantcompute_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } catch (e) { } } if (fileStore() && await qcFileSet(k, v)) return true; return false; }
function hasStore() { return !!(kv() || up() || fileStore()); }
function storeName() { return kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')); }
function keyOf(ref) { return 'qc:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return { credits: 0, used: 0, revenue_yuan: 0, revenue_coin: 0, tasks: [], entries: [] }; try { var o = JSON.parse(raw); return o && typeof o === 'object' ? o : null; } catch (e) { return null; } }
async function save(ref, o) { return dset(keyOf(ref), JSON.stringify(o)); }

function complianceFooter() {
  return {
    disclaimer: '算力任务输出基于历史数据, 不构成投资建议, 亦不代表未来收益。数据来自公开行情源, 用户自行承担风险。算力额度按实际任务扣减, 防刷。',
    data_source: 'public_market_data', generated_at: new Date().toISOString()
  };
}

// purchase: 付费后充值算力 credits 池 (高客单价: ¥199/2000币 买 20 credits)
async function purchase(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var outNo = String(payload.out_trade_no || ('coinsettle:' + Date.now())).slice(0, 80);
  var via = String(payload.paid_via || 'alipay').slice(0, 16);
  var st = await load(ref); if (!st) st = { credits: 0, used: 0, revenue_yuan: 0, revenue_coin: 0, tasks: [], entries: [] };
  for (var i = 0; i < st.entries.length; i++) { if (st.entries[i] && st.entries[i].out_trade_no === outNo) return { ok: true, duplicate: true, entry: st.entries[i] }; }
  var entry = { id: 'QC' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36), out_trade_no: outNo, via: via, credits: CREDITS_PER_PACK, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, status: 'active', at: Date.now() };
  st.entries.push(entry); st.credits += CREDITS_PER_PACK;
  if (via === 'alipay') st.revenue_yuan += PRICE_YUAN; else st.revenue_coin += PRICE_COIN;
  var ok = await save(ref, st);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: entry, credits_left: st.credits - st.used };
}

// run: 跑一个算力任务 (回测批次), 按任务类型扣 credits (fail-closed, 数据失败不扣不造假)
// 任务类型: backtest (1 credit/次), optimize (3 credits/组合), paper_combo (1 credit/组合)
async function run(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var st = await load(ref); if (!st) st = { credits: 0, used: 0, revenue_yuan: 0, revenue_coin: 0, tasks: [], entries: [] };
  var taskType = String((payload && payload.task) || 'backtest').slice(0, 24);
  // 每个任务的 credits 消耗 (真实算力, 按类型定; 不是拍脑袋)
  var costMap = { backtest: 1, optimize: 3, paper_combo: 1, overfit: 1 };
  var cost = costMap[taskType] || 1;
  if (st.credits - st.used < cost) {
    return { ok: false, error: 'need_payment', need: { yuan: PRICE_YUAN, coin: PRICE_COIN, credits: CREDITS_PER_PACK, pay_entry: '/api/pay?plan=trial&slug=qc&amount=' + PRICE_YUAN, task: taskType, cost: cost } };
  }
  var bt;
  try { bt = require('./backtest.js'); } catch (e) { return { ok: false, error: 'engine_unavailable', note: '回测引擎不可用, 未扣算力 (fail-closed, 不造假)' }; }
  var symbol = String((payload && payload.symbol) || 'BTCUSDT').slice(0, 16);
  var results = [];
  var totalCost = 0;
  if (taskType === 'optimize') {
    // 参数网格优化: N 组参数各跑一次回测 (真算力, 3 credits/组, 默认 1 组=3)
    var grid = Array.isArray((payload && payload.grid)) && (payload.grid).length ? (payload.grid) : [{ interval: '1d', limit: 90 }];
    for (var g = 0; g < grid.length; g++) {
      var rr = await bt.run({ symbol: symbol, interval: grid[g].interval || '1d', limit: grid[g].limit || 90 });
      if (!rr.ok) return { ok: false, error: 'data_fetch_failed', detail: rr.detail, note: '优化批次数据失败, 未扣算力 (fail-closed, 不造假)' };
      results.push({ leg: grid[g], metrics: rr.metrics });
      totalCost += cost;
    }
  } else if (taskType === 'paper_combo') {
    var legs = Array.isArray((payload && payload.legs)) && (payload.legs).length ? (payload.legs) : ['BTCUSDT', 'ETHUSDT'];
    for (var l = 0; l < legs.length; l++) {
      var rc = await bt.run({ symbol: legs[l], interval: (payload && payload.interval) || '1d', limit: (payload && payload.limit) || 90 });
      if (!rc.ok) return { ok: false, error: 'data_fetch_failed', detail: rc.detail, note: '组合腿数据失败, 未扣算力 (fail-closed, 不造假)' };
      results.push({ symbol: legs[l], metrics: rc.metrics });
      totalCost += 1; // 每腿 1 credit
    }
  } else {
    // 单次回测
    var rb = await bt.run({ symbol: symbol, interval: (payload && payload.interval) || '1d', limit: (payload && payload.limit) || 180 });
    if (!rb.ok) return { ok: false, error: 'data_fetch_failed', detail: rb.detail, note: '数据获取失败, 未扣算力 (fail-closed, 不造假)' };
    results.push({ symbol: symbol, metrics: rb.metrics });
    totalCost = cost;
  }
  // 扣算力 (只扣实际成功的任务数, fail-closed)
  st.used += totalCost;
  st.tasks.push({ id: 'QCT' + Date.now().toString(36), task: taskType, symbol: symbol, credits_used: totalCost, at: Date.now() });
  var sok = await save(ref, st);
  var st2 = await load(ref);
  return {
    ok: true,
    task: taskType,
    results: results,
    credits_used: totalCost,
    credits_left: st2 ? (st2.credits - st2.used) : (st.credits - st.used),
    consumed: !sok ? 0 : totalCost,
    compliance: complianceFooter()
  };
}

function summarize(ref, st) {
  st = st || { credits: 0, used: 0, revenue_yuan: 0, revenue_coin: 0, tasks: [], entries: [] };
  return { ref: ref, credits_total: st.credits, credits_used: st.used, credits_left: st.credits - st.used, tasks_count: st.tasks.length, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, credits_per_pack: CREDITS_PER_PACK, revenue_yuan: st.revenue_yuan, revenue_coin: st.revenue_coin, can_run: (st.credits - st.used) > 0 };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/quantcompute\//, '') || 'rate';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') return send(200, { ok: true, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, credits_per_pack: CREDITS_PER_PACK, store: hasStore() ? storeName() : 'none', note: '量化算力包 (按 credits 团队共享池, 币或¥); 算力输出基于历史数据, 非投资建议' });
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    var st = await load(ref); if (!st) st = { credits: 0, used: 0, revenue_yuan: 0, revenue_coin: 0, tasks: [], entries: [] };
    if (action === 'summary' || action === 'credits') { return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, st))); }
    if (action === 'ledger' || action === 'list' || action === 'tasks') { st.tasks.sort(function (a, b) { return (b.at || 0) - (a.at || 0); }); return send(200, { ok: true, count: st.tasks.length, tasks: st.tasks.slice(0, 100) }); }
    if (action === 'run' || action === 'compute') {
      var r = await run(ref, data || {});
      return send(r.ok ? 200 : (r.error === 'need_payment' ? 402 : 400), r);
    }
    if (action === 'purchase' || action === 'record') {
      var secret = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden', note: 'purchase 需 admin secret (防客户端伪造付费)' });
      var r2 = await purchase(ref, data || {});
      return send(r2.ok ? 200 : 400, r2);
    }
    return send(404, { ok: false, error: 'no_route', action: action });
  } catch (e) { return send(500, { ok: false, error: 'exception', detail: String(e && e.message) }); }
}

module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.purchase = purchase;
module.exports.run = run;
module.exports.summarize = summarize;
module.exports.hasStore = hasStore;
module.exports.PRICE_YUAN = PRICE_YUAN;
module.exports.PRICE_COIN = PRICE_COIN;
module.exports.default = onRequest;
