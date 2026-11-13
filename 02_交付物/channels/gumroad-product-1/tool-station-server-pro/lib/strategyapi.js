'use strict';
// strategyapi.js - C4 合规渠道: 付费调用策略回测 API (按调用量计费, ¥/币 双付)
// 复用 reportexport.js 同款存储原语 (KV REST -> Supabase 双写 + CN 文件回退, key 前缀 sqa:)
// 原则 (与 cashback/reportexport 一致, 诚实 + fail-closed):
//   - 服务端权威: 每次调用扣费由服务端记, 客户端不可伪造/自报
//   - fail-closed: 无存储 / ref 非法 / 未付费 / 超额 -> ok:false, 绝不白给 API 调用
//   - 幂等: 同一 (ref + 调用凭证) 只记一次
//   - 合规免责: 回测结果一律附 "非投资建议 + 历史回测不代表未来 + 数据来自公开行情源"
//   - 配额: 付费购买调用包 (N 次), 用完需再购; 超限 fail-closed 拒调
// 变现: 币走 coinsettle / ¥走支付宝; 购买调用包 = 充值该 ref 的 api_quota 额度
// Endpoints: /api/strategyapi?action=rate|summary|quota|purchase|record
//   purchase/record 需 admin secret (防客户端伪造付费); 调用由回测引擎按 token 扣减
const PRICE_YUAN = (function () { var v = parseFloat(process.env.API_PRICE_YUAN); return (isFinite(v) && v > 0) ? v : 49; })();
const PRICE_COIN = (function () { var v = parseFloat(process.env.API_PRICE_COIN); return (isFinite(v) && v > 0) ? v : 500; })();
const CALLS_PER_PACK = (function () { var v = parseInt(process.env.API_CALLS_PER_PACK); return (isFinite(v) && v > 0) ? v : 10; })();
const ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

// ---- 存储 (KV/Supabase 双写 + CN 文件回退 FILE_STORE_DIR, 独立 key 前缀 sqa:) ----
function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
function fileStore() { try { var d = process.env.FILE_STORE_DIR; return (d && String(d).trim()) ? String(d).trim() : null; } catch (e) { return null; } }
function sqaFilePath(key) { var dir = fileStore(); if (!dir) return null; var safe = String(key).replace(/[^A-Za-z0-9_.:-]/g, '_'); try { var path = require('path'); return path.join(dir, 'strategyapi', safe + '.json'); } catch (e) { return null; } }
async function sqaFileGet(key) { var p = sqaFilePath(key); if (!p) return null; try { var fs = require('node:fs/promises'); return await fs.readFile(p, 'utf8'); } catch (e) { return null; } }
async function sqaFileSet(key, val) { var p = sqaFilePath(key); if (!p) return false; try { var fs = require('node:fs/promises'); var path = require('path'); await fs.mkdir(path.dirname(p), { recursive: true }); await fs.writeFile(p, val, 'utf8'); return true; } catch (e) { return false; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/strategyapi_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } } if (fileStore()) { var f = await sqaFileGet(k); if (f !== null && f !== undefined) return f; } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/strategyapi_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } catch (e) { } } if (fileStore() && await sqaFileSet(k, v)) return true; return false; }
function hasStore() { return !!(kv() || up() || fileStore()); }
function storeName() { return kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')); }

function keyOf(ref) { return 'sqa:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return { quota: 0, calls: 0, packs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] }; try { var o = JSON.parse(raw); return o && typeof o === 'object' ? o : null; } catch (e) { return null; } }
async function save(ref, o) { return dset(keyOf(ref), JSON.stringify(o)); }

// 合规免责 (每次回测结果必附)
function complianceFooter() {
  return {
    disclaimer: '本策略回测基于历史数据, 不构成投资建议。历史表现不代表未来收益。数据来源: 平台接入的公开行情 API。用户自行承担交易风险。',
    data_source: 'public_market_data', generated_at: new Date().toISOString()
  };
}

// purchase: 由 alipay.js 在"API 调用包验证付费成功"后调用, 给该 ref 充值调用额度。
// 幂等 by out_trade_no。
async function purchase(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var outNo = String(payload.out_trade_no || ('coinsettle:' + Date.now())).slice(0, 80);
  var via = String(payload.paid_via || 'alipay').slice(0, 16);
  var st = await load(ref); if (!st) st = { quota: 0, calls: 0, packs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  for (var i = 0; i < st.entries.length; i++) { if (st.entries[i] && st.entries[i].out_trade_no === outNo) return { ok: true, duplicate: true, entry: st.entries[i] }; }
  var entry = {
    id: 'SQA' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36),
    out_trade_no: outNo, via: via, calls: CALLS_PER_PACK,
    strategy_id: String(payload.strategy_id || 'default').slice(0, 64),
    price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, status: 'active', at: Date.now()
  };
  st.entries.push(entry);
  st.quota += CALLS_PER_PACK; st.packs += 1;
  if (via === 'alipay') st.revenue_yuan += PRICE_YUAN; else st.revenue_coin += PRICE_COIN;
  var ok = await save(ref, st);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: entry, quota_left: st.quota };
}

// canCall: 该 ref 是否还有 API 调用额度 (未超额)
async function canCall(ref) {
  var st = await load(ref);
  return !!(st && st.quota > 0);
}

// consume: 回测引擎每次成功调用 API 后扣 1 次 (由服务端回测引擎调用, 非公开端点)
async function consume(ref) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var st = await load(ref); if (!st) st = { quota: 0, calls: 0, packs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  if (st.quota <= 0) return { ok: false, error: 'quota_exhausted', need: { yuan: PRICE_YUAN, coin: PRICE_COIN, calls: CALLS_PER_PACK, pay_entry: '/api/pay?plan=trial&slug=api&amount=' + PRICE_YUAN } };
  st.quota -= 1; st.calls += 1;
  var ok = await save(ref, st);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, quota_left: st.quota, total_calls: st.calls };
}

function summarize(ref, st) {
  st = st || { quota: 0, calls: 0, packs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  return {
    ref: ref, quota_left: st.quota, total_calls: st.calls, packs: st.packs,
    price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, calls_per_pack: CALLS_PER_PACK,
    revenue_yuan: st.revenue_yuan, revenue_coin: st.revenue_coin, can_call: st.quota > 0
  };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/strategyapi\/?/, '') || 'rate';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') return send(200, { ok: true, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, calls_per_pack: CALLS_PER_PACK, store: hasStore() ? storeName() : 'none', note: '付费策略回测 API (币或¥购买调用包); 合规免责已内置' });
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    var st = await load(ref); if (!st) st = { quota: 0, calls: 0, packs: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
    if (action === 'summary' || action === 'quota') { return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, st))); }
    if (action === 'ledger' || action === 'list') { st.entries.sort(function (a, b) { return (b.at || 0) - (a.at || 0); }); return send(200, { ok: true, count: st.entries.length, entries: st.entries.slice(0, 100) }); }
    if (action === 'purchase' || action === 'record') {
      // purchase/record 只能由 alipay.js 进程内调用 (验证付费后); 对外 POST 需 admin secret, 防伪造
      var secret = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden', note: 'purchase 需 admin secret (防客户端伪造付费)' });
      var r2 = await purchase(ref, data || {});
      return send(r2.ok ? 200 : 400, r2);
    }
    if (action === 'consume') {
      // consume 由回测引擎服务端调用 (非公开), 对外需 admin secret
      var secret2 = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret2 !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden', note: 'consume 需 admin secret (回测引擎服务端扣减)' });
      var r3 = await consume(ref);
      return send(r3.ok ? 200 : 400, r3);
    }
    return send(404, { ok: false, error: 'no_route', action: action });
  } catch (e) { return send(500, { ok: false, error: 'exception', detail: String(e && e.message) }); }
}

module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.purchase = purchase;
module.exports.consume = consume;
module.exports.canCall = canCall;
module.exports.summarize = summarize;
module.exports.hasStore = hasStore;
module.exports.PRICE_YUAN = PRICE_YUAN;
module.exports.PRICE_COIN = PRICE_COIN;
module.exports.default = onRequest;
