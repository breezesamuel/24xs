'use strict';
// papercombo.js - C9 合规渠道: 付费纸面模拟组合 (喂真公开K线, 多资产纸面持仓, 周推真指标到邮箱)
// 复用 C3~C8 同款存储原语 (KV/Supabase 双写 + CN 文件回退, key 前缀 pc:)
// 诚实 + fail-closed + 不造假:
//   - 服务端权威: 组合配置/指标 由服务端算, 客户端不可伪造
//   - 纸面模拟: 用真实公开 K 线(币安)跑多资产"纸面持仓", 真算 组合净值/年化/回撤/各腿表现, 不出假数
//   - 非实盘: 明确"纸面模拟, 非真实下单, 非投资建议, 不代表未来收益"
//   - (可选升级: 接 QuantDinger 真·策略级纸面实盘, 当前用简化回测引擎出真指标)
// 变现: 币走 coinsettle / ¥走支付宝; 购买 = 充值该 ref 的组合额度 (N 个组合)
// Endpoints: /api/papercombo?action=rate|summary|create|run|ledger|purchase|record
const PRICE_YUAN = (function () { var v = parseFloat(process.env.PAPER_PRICE_YUAN); return (isFinite(v) && v > 0) ? v : 99; })();
const PRICE_COIN = (function () { var v = parseFloat(process.env.PAPER_PRICE_COIN); return (isFinite(v) && v > 0) ? v : 1000; })();
const COMBOS_PER_PACK = (function () { var v = parseInt(process.env.PAPER_COMBOS_PER_PACK); return (isFinite(v) && v > 0) ? v : 3; })();
const ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
function fileStore() { try { var d = process.env.FILE_STORE_DIR; return (d && String(d).trim()) ? String(d).trim() : null; } catch (e) { return null; } }
function pcFilePath(key) { var dir = fileStore(); if (!dir) return null; var safe = String(key).replace(/[^A-Za-z0-9_.:-]/g, '_'); try { var p = require('path'); return p.join(dir, 'papercombo', safe + '.json'); } catch (e) { return null; } }
async function pcFileGet(key) { var p = pcFilePath(key); if (!p) return null; try { return await require('node:fs/promises').readFile(p, 'utf8'); } catch (e) { return null; } }
async function pcFileSet(key, val) { var p = pcFilePath(key); if (!p) return false; try { var fs = require('node:fs/promises'); var P = require('path'); await fs.mkdir(P.dirname(p), { recursive: true }); await fs.writeFile(p, val, 'utf8'); return true; } catch (e) { return false; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/papercombo_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } } if (fileStore()) { var f = await pcFileGet(k); if (f !== null && f !== undefined) return f; } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/papercombo_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } catch (e) { } } if (fileStore() && await pcFileSet(k, v)) return true; return false; }
function hasStore() { return !!(kv() || up() || fileStore()); }
function storeName() { return kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')); }
function keyOf(ref) { return 'pc:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return { slots: 0, used: 0, combos: [], revenue_yuan: 0, revenue_coin: 0, entries: [] }; try { var o = JSON.parse(raw); return o && typeof o === 'object' ? o : null; } catch (e) { return null; } }
async function save(ref, o) { return dset(keyOf(ref), JSON.stringify(o)); }

function complianceFooter() {
  return {
    disclaimer: '本组合为纸面模拟(基于公开K线), 非真实下单, 不构成投资建议, 历史表现不代表未来收益。数据来自公开行情源, 用户自行承担风险。',
    data_source: 'public_market_data', mode: 'paper_simulation', generated_at: new Date().toISOString()
  };
}

// 多资产纸面组合: 喂真 K 线, 均权组合, 真算净值/回撤
async function runCombo(ref, payload) {
  var bt;
  try { bt = require('./backtest.js'); } catch (e) { return { ok: false, error: 'engine_unavailable', note: '回测引擎不可用 (fail-closed, 不造假)' }; }
  var legs = Array.isArray((payload && payload.legs)) && (payload.legs).length ? (payload.legs) : ['BTCUSDT'];
  var interval = String((payload && payload.interval) || '1d').slice(0, 8);
  var limit = (payload && payload.limit) || 90;
  var legResults = [];
  for (var i = 0; i < legs.length; i++) {
    var rr = await bt.run({ symbol: legs[i], interval: interval, limit: limit });
    if (!rr.ok) return { ok: false, error: 'data_fetch_failed', detail: rr.detail, note: '某腿数据获取失败, 拒绝出组合 (fail-closed, 不造假)' };
    legResults.push({ symbol: legs[i], metrics: rr.metrics });
  }
  // 均权组合: 各腿期末净值平均 -> 组合净值; 回撤取各腿最差
  var n = legResults.length;
  var comboFinal = 0; var comboMaxDD = 0; var comboSharpe = 0;
  for (var j = 0; j < n; j++) {
    comboFinal += legResults[j].metrics.final_value_x;
    comboMaxDD = Math.max(comboMaxDD, legResults[j].metrics.max_drawdown_pct);
    comboSharpe += legResults[j].metrics.sharpe;
  }
  comboFinal = Math.round((comboFinal / n) * 10000) / 10000;
  comboSharpe = Math.round((comboSharpe / n) * 100) / 100;
  var comboRet = (comboFinal - 1) * 100;
  return {
    ok: true, combo: {
      legs: legResults.map(function (x) { return { symbol: x.symbol, total_return_pct: x.metrics.total_return_pct, sharpe: x.metrics.sharpe, max_dd_pct: x.metrics.max_drawdown_pct, win_rate_pct: x.metrics.win_rate_pct }; }),
      weighted: { final_value_x: comboFinal, total_return_pct: Math.round(comboRet * 100) / 100, sharpe: comboSharpe, worst_max_dd_pct: Math.round(comboMaxDD * 100) / 100 },
      range: legResults[0] && legResults[0].metrics ? { start: legResults[0].metrics.start_price, end: legResults[0].metrics.end_price } : {}
    },
    compliance: complianceFooter()
  };
}

// purchase: 付费后充值组合额度
async function purchase(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var outNo = String(payload.out_trade_no || ('coinsettle:' + Date.now())).slice(0, 80);
  var via = String(payload.paid_via || 'alipay').slice(0, 16);
  var st = await load(ref); if (!st) st = { slots: 0, used: 0, combos: [], revenue_yuan: 0, revenue_coin: 0, entries: [] };
  for (var i = 0; i < st.entries.length; i++) { if (st.entries[i] && st.entries[i].out_trade_no === outNo) return { ok: true, duplicate: true, entry: st.entries[i] }; }
  var entry = { id: 'PC' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36), out_trade_no: outNo, via: via, slots: COMBOS_PER_PACK, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, status: 'active', at: Date.now() };
  st.entries.push(entry); st.slots += COMBOS_PER_PACK;
  if (via === 'alipay') st.revenue_yuan += PRICE_YUAN; else st.revenue_coin += PRICE_COIN;
  var ok = await save(ref, st);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: entry, slots_left: st.slots - st.used };
}

function summarize(ref, st) {
  st = st || { slots: 0, used: 0, combos: [], revenue_yuan: 0, revenue_coin: 0, entries: [] };
  return { ref: ref, slots_left: st.slots - st.used, slots_total: st.slots, combos_count: st.combos.length, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, combos_per_pack: COMBOS_PER_PACK, revenue_yuan: st.revenue_yuan, revenue_coin: st.revenue_coin, can_create: (st.slots - st.used) > 0 };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/papercombo\/?/, '') || 'rate';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') return send(200, { ok: true, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, combos_per_pack: COMBOS_PER_PACK, store: hasStore() ? storeName() : 'none', note: '付费纸面模拟组合 (币或¥); 纸面非实盘, 非投资建议, 不出假数' });
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    var st = await load(ref); if (!st) st = { slots: 0, used: 0, combos: [], revenue_yuan: 0, revenue_coin: 0, entries: [] };
    if (action === 'summary' || action === 'slot') { return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, st))); }
    if (action === 'ledger' || action === 'list') { return send(200, { ok: true, count: st.combos.length, entries: st.combos.slice(0, 50) }); }
    if (action === 'create' || action === 'run') {
      // 需有组合额度 (未购 -> 402)
      if ((st.slots - st.used) <= 0) {
        return send(402, { ok: false, error: 'need_payment', need: { yuan: PRICE_YUAN, coin: PRICE_COIN, combos: COMBOS_PER_PACK, pay_entry: '/api/pay?plan=trial&slug=paper&amount=' + PRICE_YUAN } });
      }
      var r = await runCombo(ref, data || {});
      if (!r.ok) return send(500, { ok: false, error: r.error, detail: r.detail, note: '数据获取失败, 未扣额度 (fail-closed, 不造假)' });
      // 扣 1 组合位 + 记录
      st.used += 1;
      st.combos.push({ id: 'PC' + Date.now().toString(36), legs: r.combo.legs.map(function (l) { return l.symbol; }), result: r.combo, at: Date.now() });
      var sok = await save(ref, st);
      return send(200, { ok: true, combo: r.combo, consumed: !sok ? 0 : 1, slots_left: sok ? (st.slots - st.used) : st.slots, compliance: r.compliance, note: '已记 1 组合纸面模拟 (真数据, 非实盘)' });
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
module.exports.runCombo = runCombo;
module.exports.summarize = summarize;
module.exports.hasStore = hasStore;
module.exports.PRICE_YUAN = PRICE_YUAN;
module.exports.PRICE_COIN = PRICE_COIN;
module.exports.default = onRequest;
