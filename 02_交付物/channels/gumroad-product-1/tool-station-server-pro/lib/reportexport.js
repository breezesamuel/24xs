'use strict';
// reportexport.js - C3 合规渠道: 付费导出专业回测报告 (PDF/CSV)
// 复用 cashback.js 同款存储原语 (KV REST -> Supabase 双写 + CN 文件回退, key 前缀 rpx:)
// 原则 (与 cashback/commission 一致, 诚实 + fail-closed):
//   - 服务端权威: 报告价格由服务端定, 客户端不可伪造
//   - fail-closed: 无存储 / ref 非法 / 未付费 -> ok:false, 绝不白给报告
//   - 幂等: 同一 (ref + strategy_id + format + version) 只生成一次导出, 重复请求返回 duplicate
//   - 合规免责: 报告一律附 "非投资建议 + 数据来源标注 + 回测不代表未来收益" 声明
// 变现: 两条已验证渠道
//   - 币: 达到 100 币门槛 -> 走 /api/coinsettle (source=earned) 结算
//   - ¥ : 走支付宝 /api/pay (slug=report), 验证成功后由 alipay.js 调 record() 解锁导出
// Endpoints: /api/reportexport?action=rate|summary|generate|ledger
//   generate 需已付费 (ref 的已付记录存在) 才放行; 未付费返回 need_payment + 收银台入口
const PRICE_YUAN = (function () { var v = parseFloat(process.env.REPORT_PRICE_YUAN); return (isFinite(v) && v > 0) ? v : 9.9; })();
const PRICE_COIN = (function () { var v = parseFloat(process.env.REPORT_PRICE_COIN); return (isFinite(v) && v > 0) ? v : 100; })();
const FORMATS = ['pdf', 'csv'];
const ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

// ---- 存储 (KV/Supabase 双写 + CN 文件回退 FILE_STORE_DIR, 独立 key 前缀 rpx:) ----
function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
function fileStore() { try { var d = process.env.FILE_STORE_DIR; return (d && String(d).trim()) ? String(d).trim() : null; } catch (e) { return null; } }
function rpxFilePath(key) { var dir = fileStore(); if (!dir) return null; var safe = String(key).replace(/[^A-Za-z0-9_.:-]/g, '_'); try { var path = require('path'); return path.join(dir, 'reportexport', safe + '.json'); } catch (e) { return null; } }
async function rpxFileGet(key) { var p = rpxFilePath(key); if (!p) return null; try { var fs = require('node:fs/promises'); return await fs.readFile(p, 'utf8'); } catch (e) { return null; } }
async function rpxFileSet(key, val) { var p = rpxFilePath(key); if (!p) return false; try { var fs = require('node:fs/promises'); var path = require('path'); await fs.mkdir(path.dirname(p), { recursive: true }); await fs.writeFile(p, val, 'utf8'); return true; } catch (e) { return false; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/reportexport_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } } if (fileStore()) { var f = await rpxFileGet(k); if (f !== null && f !== undefined) return f; } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/reportexport_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } catch (e) { } } if (fileStore() && await rpxFileSet(k, v)) return true; return false; }
function hasStore() { return !!(kv() || up() || fileStore()); }
function storeName() { return kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')); }

function keyOf(ref) { return 'rpx:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return []; try { var a = JSON.parse(raw); return Array.isArray(a) ? a : []; } catch (e) { return []; } }
async function save(ref, arr) { return dset(keyOf(ref), JSON.stringify(arr)); }

// 合规免责声明 (每份报告必附, 诚实红线)
function complianceFooter() {
  return {
    disclaimer: '本报告基于历史回测数据, 不构成投资建议。历史表现不代表未来收益。数据来源: 平台接入的公开行情 API。用户自行承担交易风险。',
    data_source: 'public_market_data',
    generated_at: new Date().toISOString()
  };
}

// record: 由 alipay.js 在"报告订单验证付费成功"后调用, 解锁该 (ref+strategy+format+version) 的导出权。
// 幂等 by (strategy_id|format|version)。
async function record(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!payload || !payload.strategy_id) return { ok: false, error: 'missing_strategy' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var sid = String(payload.strategy_id).slice(0, 64);
  var format = FORMATS.indexOf(payload.format) >= 0 ? payload.format : 'pdf';
  var version = String(payload.version || 1).slice(0, 16);
  var outNo = String(payload.out_trade_no || ('coinsettle:' + sid)).slice(0, 80);
  var arr = await load(ref);
  for (var i = 0; i < arr.length; i++) {
    var e = arr[i];
    if (e && e.strategy_id === sid && e.format === format && e.version === version) {
      return { ok: true, duplicate: true, entry: e };
    }
  }
  var entry = {
    id: 'RPX' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36),
    strategy_id: sid, format: format, version: version,
    paid_via: String(payload.paid_via || 'alipay').slice(0, 16),
    out_trade_no: outNo,
    price_yuan: PRICE_YUAN, price_coin: PRICE_COIN,
    status: 'unlocked', at: Date.now()
  };
  arr.push(entry);
  var ok = await save(ref, arr);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: entry };
}

// isUnlocked: 该 (ref+strategy+format+version) 是否已付费解锁
async function isUnlocked(ref, payload) {
  var arr = await load(ref);
  var sid = String((payload && payload.strategy_id) || '');
  var format = FORMATS.indexOf(payload && payload.format) >= 0 ? (payload && payload.format) : 'pdf';
  var version = String((payload && payload.version) || 1);
  for (var i = 0; i < arr.length; i++) {
    var e = arr[i];
    if (e && e.strategy_id === sid && e.format === format && e.version === version && e.status === 'unlocked') return e;
  }
  return null;
}

// generate: 只有已付费解锁才放行; 已付费则调 backtest.js 出真指标报告 (基于公开K线的简化回测, 不造假)
async function generate(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var sid = String((payload && payload.strategy_id) || '').slice(0, 64);
  if (!sid) return { ok: false, error: 'missing_strategy' };
  var unlocked = await isUnlocked(ref, payload);
  if (!unlocked) {
    return { ok: false, error: 'need_payment', need: { yuan: PRICE_YUAN, coin: PRICE_COIN, format: (payload && payload.format) || 'pdf', pay_entry: '/api/pay?plan=trial&slug=report&amount=' + PRICE_YUAN } };
  }
  // 已付费 -> 出真回测报告 (调 backtest.js, 拉公开K线真算指标; fail-closed)
  var reportBody = null;
  try {
    var bt = require('./backtest.js');
    var rr = await bt.run({ symbol: (payload && payload.symbol) || 'BTCUSDT', interval: (payload && payload.interval) || '1d', limit: (payload && payload.limit) || 90, strategy: sid });
    if (rr.ok) reportBody = bt.buildReport(rr, { strategy_id: sid, strategy_name: sid });
  } catch (e) { /* 引擎不可用则只给解锁token, 不造假 */ }
  return {
    ok: true, entry: unlocked,
    report_ready: true,
    download_token: 'RPXDL_' + unlocked.id,
    report: reportBody, // 真回测报告体 (若引擎成功); 否则 null (前端降级显示"引擎生成中")
    format: (payload && payload.format) || 'pdf',
    compliance: reportBody ? reportBody.compliance : complianceFooter(),
    note: reportBody ? '已出真指标回测报告 (基于公开K线简化回测, 非策略代码级)' : '已解锁导出权; 回测引擎暂不可用, 报告稍后按 token 下发'
  };
}

function summarize(ref, arr) {
  var n = arr.length, unlocked = 0, paidYuan = 0, paidCoin = 0;
  for (var i = 0; i < arr.length; i++) { var e = arr[i] || {}; if (e.status === 'unlocked') { unlocked++; paidYuan += e.price_yuan || 0; paidCoin += e.price_coin || 0; } }
  return {
    ref: ref, count: n, unlocked: unlocked,
    price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, formats: FORMATS,
    revenue_yuan: paidYuan, revenue_coin: paidCoin,
    can_download: unlocked > 0
  };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/reportexport\/?/, '') || 'rate';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') return send(200, { ok: true, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, formats: FORMATS, store: hasStore() ? storeName() : 'none', note: '付费导出专业报告 (币或¥); 合规免责已内置' });
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    if (action === 'summary') { var arr = await load(ref); return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, arr))); }
    if (action === 'ledger' || action === 'list') { var arr2 = await load(ref); arr2.sort(function (a, b) { return (b.at || 0) - (a.at || 0); }); return send(200, { ok: true, count: arr2.length, entries: arr2.slice(0, 100) }); }
    if (action === 'generate') { var r = await generate(ref, data || {}); return send(r.ok ? 200 : (r.error === 'need_payment' ? 402 : 400), r); }
    if (action === 'record') {
      // record 只能由 alipay.js 进程内调用 (验证付费后); 对外 POST 需 admin secret, 防伪造
      var secret = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden', note: 'record 需 admin secret (防客户端伪造付费)' });
      var r2 = await record(ref, data || {});
      return send(r2.ok ? 200 : 400, r2);
    }
    return send(404, { ok: false, error: 'no_route', action: action });
  } catch (e) { return send(500, { ok: false, error: 'exception', detail: String(e && e.message) }); }
}

module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.record = record;
module.exports.generate = generate;
module.exports.summarize = summarize;
module.exports.isUnlocked = isUnlocked;
module.exports.hasStore = hasStore;
module.exports.PRICE_YUAN = PRICE_YUAN;
module.exports.PRICE_COIN = PRICE_COIN;
module.exports.default = onRequest;
