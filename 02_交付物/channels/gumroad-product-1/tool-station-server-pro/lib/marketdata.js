'use strict';
// marketdata.js - C5 合规渠道: 行情/市场情报数据 API 按月订阅 (¥/币 双付)
// 复用 reportexport.js 同款存储原语 (KV REST -> Supabase 双写 + CN 文件回退, key 前缀 md:)
// 原则 (诚实 + fail-closed):
//   - 服务端权威: 订阅生效/到期 由服务端算, 客户端不可伪造
//   - fail-closed: 无存储 / ref 非法 / 未订阅 / 已到期 -> ok:false, 绝不误放行数据
//   - 幂等: 同一 (ref + 订阅周期 out_trade_no) 只记一次
//   - 合规免责: 行情数据一律附 "数据来自公开行情源 + 不构成投资建议 + 实时性以源为准"
// 变现: 币走 coinsettle / ¥走支付宝; 购买 = 充值该 ref 的订阅有效期 (N 天)
// Endpoints: /api/marketdata?action=rate|status|summary|purchase|record
//   purchase/record 需 admin secret (防客户端伪造付费)
const SUB_DAYS = (function () { var v = parseInt(process.env.MARKET_SUB_DAYS); return (isFinite(v) && v > 0) ? v : 30; })();
const PRICE_YUAN = (function () { var v = parseFloat(process.env.MARKET_PRICE_YUAN); return (isFinite(v) && v > 0) ? v : 19.9; })();
const PRICE_COIN = (function () { var v = parseFloat(process.env.MARKET_PRICE_COIN); return (isFinite(v) && v > 0) ? v : 200; })();
const ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

// ---- 存储 (KV/Supabase 双写 + CN 文件回退 FILE_STORE_DIR, 独立 key 前缀 md:) ----
function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
function fileStore() { try { var d = process.env.FILE_STORE_DIR; return (d && String(d).trim()) ? String(d).trim() : null; } catch (e) { return null; } }
function mdFilePath(key) { var dir = fileStore(); if (!dir) return null; var safe = String(key).replace(/[^A-Za-z0-9_.:-]/g, '_'); try { var path = require('path'); return path.join(dir, 'marketdata', safe + '.json'); } catch (e) { return null; } }
async function mdFileGet(key) { var p = mdFilePath(key); if (!p) return null; try { var fs = require('node:fs/promises'); return await fs.readFile(p, 'utf8'); } catch (e) { return null; } }
async function mdFileSet(key, val) { var p = mdFilePath(key); if (!p) return false; try { var fs = require('node:fs/promises'); var path = require('path'); await fs.mkdir(path.dirname(p), { recursive: true }); await fs.writeFile(p, val, 'utf8'); return true; } catch (e) { return false; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/marketdata_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } } if (fileStore()) { var f = await mdFileGet(k); if (f !== null && f !== undefined) return f; } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/marketdata_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } catch (e) { } } if (fileStore() && await mdFileSet(k, v)) return true; return false; }
function hasStore() { return !!(kv() || up() || fileStore()); }
function storeName() { return kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')); }

function keyOf(ref) { return 'md:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return { active_until: 0, periods: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] }; try { var o = JSON.parse(raw); return o && typeof o === 'object' ? o : null; } catch (e) { return null; } }
async function save(ref, o) { return dset(keyOf(ref), JSON.stringify(o)); }

// 合规免责 (行情数据必附)
function complianceFooter() {
  return {
    disclaimer: '行情/市场数据来自平台接入的公开行情 API, 不构成投资建议。数据实时性以数据源为准, 可能存在延迟。用户自行判断, 风险自负。',
    data_source: 'public_market_data', generated_at: new Date().toISOString()
  };
}

// purchase: 由 alipay.js 在"订阅验证付费成功"后调用, 给该 ref 充值订阅有效期 (累加 SUB_DAYS)。
// 幂等 by out_trade_no。
async function purchase(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var outNo = String(payload.out_trade_no || ('coinsettle:' + Date.now())).slice(0, 80);
  var via = String(payload.paid_via || 'alipay').slice(0, 16);
  var st = await load(ref); if (!st) st = { active_until: 0, periods: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  for (var i = 0; i < st.entries.length; i++) { if (st.entries[i] && st.entries[i].out_trade_no === outNo) return { ok: true, duplicate: true, entry: st.entries[i] }; }
  var now = Date.now();
  // 累加有效期: 从当前 active_until (若未到期) 或 now 起算
  var base = (st.active_until > now) ? st.active_until : now;
  var entry = {
    id: 'MD' + now.toString(36) + Math.floor(Math.random() * 1e6).toString(36),
    out_trade_no: outNo, via: via, days: SUB_DAYS,
    data_source: String(payload.data_source || 'public_candles').slice(0, 64),
    price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, status: 'active', at: now
  };
  st.entries.push(entry);
  st.active_until = base + SUB_DAYS * 86400000; st.periods += 1;
  if (via === 'alipay') st.revenue_yuan += PRICE_YUAN; else st.revenue_coin += PRICE_COIN;
  var ok = await save(ref, st);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: entry, active_until: st.active_until };
}

// isActive: 该 ref 订阅是否有效 (now < active_until)
async function isActive(ref) {
  var st = await load(ref);
  return !!(st && st.active_until > Date.now());
}

// access: 数据端点鉴权 — 只有有效订阅才放行, 返回合规页脚; 未订阅/到期 -> need_payment
async function access(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var active = await isActive(ref);
  if (!active) {
    return { ok: false, error: 'need_payment', need: { yuan: PRICE_YUAN, coin: PRICE_COIN, days: SUB_DAYS, pay_entry: '/api/pay?plan=trial&slug=market&amount=' + PRICE_YUAN } };
  }
  var st = await load(ref);
  return {
    ok: true, active: true, active_until: st.active_until,
    data: { note: '行情数据由回测引擎/行情服务按订阅下发 (此处仅鉴权 + 合规)' },
    compliance: complianceFooter()
  };
}

function summarize(ref, st) {
  st = st || { active_until: 0, periods: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  var active = st.active_until > Date.now();
  return {
    ref: ref, active: active, active_until: st.active_until, periods: st.periods,
    sub_days: SUB_DAYS, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN,
    revenue_yuan: st.revenue_yuan, revenue_coin: st.revenue_coin
  };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/marketdata\/?/, '') || 'rate';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') return send(200, { ok: true, sub_days: SUB_DAYS, price_yuan: PRICE_YUAN, price_coin: PRICE_COIN, store: hasStore() ? storeName() : 'none', note: '行情/市场情报数据订阅 (币或¥, 按月); 合规免责已内置' });
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    var st = await load(ref); if (!st) st = { active_until: 0, periods: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
    if (action === 'status' || action === 'summary') { return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, st))); }
    if (action === 'ledger' || action === 'list') { st.entries.sort(function (a, b) { return (b.at || 0) - (a.at || 0); }); return send(200, { ok: true, count: st.entries.length, entries: st.entries.slice(0, 100) }); }
    if (action === 'access' || action === 'data') {
      var ra = await access(ref, data || {});
      return send(ra.ok ? 200 : (ra.error === 'need_payment' ? 402 : 400), ra);
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
module.exports.isActive = isActive;
module.exports.access = access;
module.exports.summarize = summarize;
module.exports.hasStore = hasStore;
module.exports.PRICE_YUAN = PRICE_YUAN;
module.exports.PRICE_COIN = PRICE_COIN;
module.exports.default = onRequest;
