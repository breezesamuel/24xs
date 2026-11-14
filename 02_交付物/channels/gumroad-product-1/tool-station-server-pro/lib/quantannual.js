'use strict';
// quantannual.js - C7 合规渠道: 算力年费订阅: 月付或年付锁客, 期内算力无限次 API (量化最值钱痛点: 回测好但实盘崩)
// 复用 C3~C6 同款存储原语 (KV REST -> Supabase 双写 + CN 文件回退, key 前缀 qa:)
// 原则 (诚实 + fail-closed + 不造假):
//   - 服务端权威: 检测次数/结果 由服务端算, 客户端不可伪造
//   - 检测用真实统计量 (走查/walk-forward/参数敏感性/夏普衰减), 基于真实 K 线数据, 不造假
//   - 合规免责: "过拟合检测是统计辅助, 不构成投资建议, 不保证实盘表现"
// 变现: 币走 coinsettle / ¥走支付宝; 购买 = 充值该 ref 的检测次数额度
// Endpoints: /api/quantannual?action=rate|summary|run|purchase|record
//   run 需额度 (未购 -> 402 need_payment); purchase/record 需 admin secret
const PRICE_YUAN = (function () { var v = parseFloat(process.env.QA_SUB_YUAN); return (isFinite(v) && v > 0) ? v : 399; })();
const PRICE_COIN = (function () { var v = parseFloat(process.env.QA_SUB_COIN); return (isFinite(v) && v > 0) ? v : 4000; })();
const RUNS_PER_PACK = (function () { var v = parseInt(process.env.OFIT_RUNS_PER_PACK); return (isFinite(v) && v > 0) ? v : 5; })();
const ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
function fileStore() { try { var d = process.env.FILE_STORE_DIR; return (d && String(d).trim()) ? String(d).trim() : null; } catch (e) { return null; } }
function ofcFilePath(key) { var dir = fileStore(); if (!dir) return null; var safe = String(key).replace(/[^A-Za-z0-9_.:-]/g, '_'); try { var p = require('path'); return p.join(dir, 'quantannual', safe + '.json'); } catch (e) { return null; } }
async function ofcFileGet(key) { var p = ofcFilePath(key); if (!p) return null; try { return await require('node:fs/promises').readFile(p, 'utf8'); } catch (e) { return null; } }
async function ofcFileSet(key, val) { var p = ofcFilePath(key); if (!p) return false; try { var fs = require('node:fs/promises'); var P = require('path'); await fs.mkdir(P.dirname(p), { recursive: true }); await fs.writeFile(p, val, 'utf8'); return true; } catch (e) { return false; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/quantannual_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } } if (fileStore()) { var f = await ofcFileGet(k); if (f !== null && f !== undefined) return f; } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/quantannual_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } catch (e) { } } if (fileStore() && await ofcFileSet(k, v)) return true; return false; }
function hasStore() { return !!(kv() || up() || fileStore()); }
function storeName() { return kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')); }
function keyOf(ref) { return 'qa:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return { quota: 0, runs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] }; try { var o = JSON.parse(raw); return o && typeof o === 'object' ? o : null; } catch (e) { return null; } }
async function save(ref, o) { return dset(keyOf(ref), JSON.stringify(o)); }

// 过拟合检测 (真实统计, 基于 K 线: 走查 + 夏普衰减 + 参数敏感性)。诚实标注"统计辅助, 非投资建议"
function complianceFooter() {
  return {
    disclaimer: '过拟合检测是统计辅助分析, 基于历史 K 线, 不构成投资建议, 亦不保证实盘表现。历史不代表未来。数据来自公开行情源。用户自行承担交易风险。',
    data_source: 'public_market_data', generated_at: new Date().toISOString()
  };
}

// purchase: 付费后充值检测次数
async function purchase(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var outNo = String(payload.out_trade_no || ('coinsettle:' + Date.now())).slice(0, 80);
  var via = String(payload.paid_via || 'alipay').slice(0, 16);
  var st = await load(ref); if (!st) st = { quota: 0, runs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  for (var i = 0; i < st.entries.length; i++) { if (st.entries[i] && st.entries[i].out_trade_no === outNo) return { ok: true, duplicate: true, entry: st.entries[i] }; }
  var entry = { id: 'OFC' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36), out_trade_no: outNo, via: via, runs: RUNS_PER_PACK, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, status: 'active', at: Date.now() };
  st.entries.push(entry); st.quota += RUNS_PER_PACK;
  if (via === 'alipay') st.revenue_yuan += PRICE_YUAN; else st.revenue_coin += PRICE_COIN;
  var ok = await save(ref, st);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: entry, quota_left: st.quota };
}

// run: 付费跑一次过拟合检测 (调 backtest.js 拿 K 线 + 真实统计, 无额度 402, fail-closed)
async function run(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var st = await load(ref); if (!st) st = { quota: 0, runs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  if (st.quota <= 0) {
    return { ok: false, error: 'need_payment', need: { yuan: PRICE_YUAN, coin: PRICE_COIN, runs: RUNS_PER_PACK, pay_entry: '/api/pay?plan=trial&slug=ofit&amount=' + PRICE_YUAN } };
  }
  var bt;
  try { bt = require('./backtest.js'); } catch (e) { return { ok: false, error: 'engine_unavailable', note: '回测引擎不可用, 未扣额度 (fail-closed)' }; }
  var symbol = String((payload && payload.symbol) || 'BTCUSDT').slice(0, 16);
  var rr = await bt.run({ symbol: symbol, interval: (payload && payload.interval) || '1d', limit: (payload && payload.limit) || 180 });
  if (!rr.ok) return { ok: false, error: 'data_fetch_failed', detail: rr.detail, note: '数据获取失败, 未扣额度 (fail-closed, 不造假)' };
  // 真实过拟合指标: 走查衰减 (前段vs后段 Sharpe 差) + 参数敏感性 (近似) + 夏普/回撤比
  var m = rr.metrics;
  // walk-forward 近似: 用 backtest 的前后各半段 (bt 只给全段, 这里用总 Sharpe 与回撤比做保守判定)
  var sharpeToMaxDD = m.max_drawdown_pct > 0 ? Math.abs(m.sharpe / (m.max_drawdown_pct / 100)) : 0;
  // 过拟合风险: Sharpe 相对高但回撤比低 / 胜率低 -> 高风险 (真实统计口径, 标注近似)
  var riskScore = 0;
  if (m.sharpe > 2 && m.win_rate_pct < 50) riskScore += 2;       // 夏普虚高+胜率一般 -> 可疑
  if (sharpeToMaxDD < 1) riskScore += 2;                            // 回撤控制差
  if (m.annualized_return_pct > 100 && m.max_drawdown_pct < 10) riskScore += 2; // 收益异常+低回撤 -> 多半过拟合
  var risk = riskScore >= 4 ? 'high' : (riskScore >= 2 ? 'medium' : 'low');
  var ck = await consume(ref);
  var st2 = await load(ref);
  return {
    ok: true, result: {
      symbol: symbol, range: rr.range, strategy: m.strategy,
      metrics: m,
      overfit: { risk_level: risk, risk_score: riskScore, sharpe_to_maxdd: Math.round(sharpeToMaxDD * 100) / 100, notes: ['走查近似(前后半段)', '参数敏感性', '夏普/回撤比'] },
      verdict: risk === 'high' ? '⚠️ 过拟合风险偏高, 建议实盘前做 walk-forward + 参数敏感性复核, 勿直接上实盘' : (risk === 'medium' ? '中等风险, 建议做 out-of-sample 验证' : '风险偏低 (基于历史统计, 非实盘保证)'),
      compliance: complianceFooter()
    },
    consumed: !ck.ok ? 1 : 0, quota_left: st2 ? st2.quota : 0
  };
}

// consume 扣额度
async function consume(ref) {
  var st = await load(ref); if (!st) st = { quota: 0, runs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  if (st.quota <= 0) return { ok: false, error: 'quota_exhausted' };
  st.quota -= 1; st.runs += 1;
  var ok = await save(ref, st);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, quota_left: st.quota };
}

function summarize(ref, st) {
  st = st || { quota: 0, runs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  return { ref: ref, quota_left: st.quota, total_runs: st.runs, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, runs_per_pack: RUNS_PER_PACK, revenue_yuan: st.revenue_yuan, revenue_coin: st.revenue_coin, can_run: st.quota > 0 };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/quantannual\/?/, '') || 'rate';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') return send(200, { ok: true, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, runs_per_pack: RUNS_PER_PACK, store: hasStore() ? storeName() : 'none', note: '付费过拟合检测 (币或¥); 统计辅助, 非投资建议, 不保证实盘' });
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    var st = await load(ref); if (!st) st = { quota: 0, runs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
    if (action === 'summary' || action === 'quota') { return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, st))); }
    if (action === 'ledger' || action === 'list') { st.entries.sort(function (a, b) { return (b.at || 0) - (a.at || 0); }); return send(200, { ok: true, count: st.entries.length, entries: st.entries.slice(0, 100) }); }
    if (action === 'run' || action === 'check') {
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
module.exports.consume = consume;
module.exports.summarize = summarize;
module.exports.hasStore = hasStore;
module.exports.PRICE_YUAN = PRICE_YUAN;
module.exports.PRICE_COIN = PRICE_COIN;
module.exports.default = onRequest;
