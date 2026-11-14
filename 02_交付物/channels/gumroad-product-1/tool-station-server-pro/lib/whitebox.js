'use strict';
// whitebox.js - C8 合规渠道: 团队/白标 API 包 (B端高客单价, 按席位/白标授权收费)
// 复用 C3~C7 同款存储原语 (KV/Supabase 双写 + CN 文件回退, key 前缀 wb:)
// 合规 (诚实 + fail-closed):
//   - 服务端权威: 席位/白标授权 由服务端算, 客户端不可伪造
//   - 白标 = 给团队/合作方 API 调用权 (带他们的 brand 标识), 非把平台转售给未授权方
//   - 合规免责: API 结果附 "非投资建议", 白标方对其对外展示负最终责任
// 变现: 币走 coinsettle / ¥走支付宝; 购买 = 充值该 ref 的席位额度
// Endpoints: /api/whitebox?action=rate|summary|seat|purchase|record
const SEAT_PRICE_YUAN = (function () { var v = parseFloat(process.env.WB_SEAT_YUAN); return (isFinite(v) && v > 0) ? v : 199; })();
const SEAT_PRICE_COIN = (function () { var v = parseFloat(process.env.WB_SEAT_COIN); return (isFinite(v) && v > 0) ? v : 2000; })();
const SEATS_PER_PACK = (function () { var v = parseInt(process.env.WB_SEATS_PER_PACK); return (isFinite(v) && v > 0) ? v : 3; })();
const ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
function fileStore() { try { var d = process.env.FILE_STORE_DIR; return (d && String(d).trim()) ? String(d).trim() : null; } catch (e) { return null; } }
function wbFilePath(key) { var dir = fileStore(); if (!dir) return null; var safe = String(key).replace(/[^A-Za-z0-9_.:-]/g, '_'); try { var p = require('path'); return p.join(dir, 'whitebox', safe + '.json'); } catch (e) { return null; } }
async function wbFileGet(key) { var p = wbFilePath(key); if (!p) return null; try { return await require('node:fs/promises').readFile(p, 'utf8'); } catch (e) { return null; } }
async function wbFileSet(key, val) { var p = wbFilePath(key); if (!p) return false; try { var fs = require('node:fs/promises'); var P = require('path'); await fs.mkdir(P.dirname(p), { recursive: true }); await fs.writeFile(p, val, 'utf8'); return true; } catch (e) { return false; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/whitebox_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } } if (fileStore()) { var f = await wbFileGet(k); if (f !== null && f !== undefined) return f; } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/whitebox_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } catch (e) { } } if (fileStore() && await wbFileSet(k, v)) return true; return false; }
function hasStore() { return !!(kv() || up() || fileStore()); }
function storeName() { return kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')); }
function keyOf(ref) { return 'wb:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return { seats: 0, used: 0, revenue_yuan: 0, revenue_coin: 0, brand: '', entries: [] }; try { var o = JSON.parse(raw); return o && typeof o === 'object' ? o : null; } catch (e) { return null; } }
async function save(ref, o) { return dset(keyOf(ref), JSON.stringify(o)); }

function complianceFooter() {
  return {
    disclaimer: '白标 API 输出基于历史数据, 不构成投资建议。白标授权方对其对外展示与决策负最终责任。数据来自公开行情源, 历史不代表未来。',
    data_source: 'public_market_data', generated_at: new Date().toISOString()
  };
}

// purchase: 付费后充值席位 (B端按席位收费, 高客单价)
async function purchase(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var outNo = String(payload.out_trade_no || ('coinsettle:' + Date.now())).slice(0, 80);
  var via = String(payload.paid_via || 'alipay').slice(0, 16);
  var brand = String(payload.brand || '').slice(0, 64); // 白标方 brand 标识
  var st = await load(ref); if (!st) st = { seats: 0, used: 0, revenue_yuan: 0, revenue_coin: 0, brand: '', entries: [] };
  for (var i = 0; i < st.entries.length; i++) { if (st.entries[i] && st.entries[i].out_trade_no === outNo) return { ok: true, duplicate: true, entry: st.entries[i] }; }
  var entry = { id: 'WB' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36), out_trade_no: outNo, via: via, seats: SEATS_PER_PACK, brand: brand, price_yuan: SEAT_PRICE_YUAN, price_coin: SEAT_PRICE_COIN, status: 'active', at: Date.now() };
  st.entries.push(entry); st.seats += SEATS_PER_PACK;
  if (brand) st.brand = brand;
  if (via === 'alipay') st.revenue_yuan += SEAT_PRICE_YUAN; else st.revenue_coin += SEAT_PRICE_COIN;
  var ok = await save(ref, st);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: entry, seats_left: st.seats };
}

// claimSeat: 占用一个席位 (团队加人时, 服务端扣, fail-closed)
async function claimSeat(ref, payload) {
  var st = await load(ref); if (!st) st = { seats: 0, used: 0, revenue_yuan: 0, revenue_coin: 0, brand: '', entries: [] };
  if (st.seats - st.used <= 0) return { ok: false, error: 'no_seat', note: '席位已用完, 需再购' };
  st.used += 1;
  var ok = await save(ref, st);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, seats_left: st.seats - st.used, compliance: complianceFooter() };
}

function summarize(ref, st) {
  st = st || { seats: 0, used: 0, revenue_yuan: 0, revenue_coin: 0, brand: '', entries: [] };
  return { ref: ref, seats_total: st.seats, seats_used: st.used, seats_left: st.seats - st.used, brand: st.brand, price_yuan: SEAT_PRICE_YUAN, price_coin: SEAT_PRICE_COIN, seats_per_pack: SEATS_PER_PACK, revenue_yuan: st.revenue_yuan, revenue_coin: st.revenue_coin };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/whitebox\/?/, '') || 'rate';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') return send(200, { ok: true, seat_price_yuan: SEAT_PRICE_YUAN, seat_price_coin: SEAT_PRICE_COIN, seats_per_pack: SEATS_PER_PACK, store: hasStore() ? storeName() : 'none', note: '团队/白标 API 包 (按席位, 币或¥); 白标方对外展示自负责任, 非投资建议' });
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    var st = await load(ref); if (!st) st = { seats: 0, used: 0, revenue_yuan: 0, revenue_coin: 0, brand: '', entries: [] };
    if (action === 'summary' || action === 'seat') { return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, st))); }
    if (action === 'ledger' || action === 'list') { st.entries.sort(function (a, b) { return (b.at || 0) - (a.at || 0); }); return send(200, { ok: true, count: st.entries.length, entries: st.entries.slice(0, 100) }); }
    if (action === 'claim' || action === 'claim_seat') {
      var secret = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden', note: 'claim_seat 需 admin secret (服务端扣席位)' });
      var rc = await claimSeat(ref, data || {});
      return send(rc.ok ? 200 : 400, rc);
    }
    if (action === 'purchase' || action === 'record') {
      var secret2 = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret2 !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden', note: 'purchase 需 admin secret (防客户端伪造付费)' });
      var r2 = await purchase(ref, data || {});
      return send(r2.ok ? 200 : 400, r2);
    }
    return send(404, { ok: false, error: 'no_route', action: action });
  } catch (e) { return send(500, { ok: false, error: 'exception', detail: String(e && e.message) }); }
}

module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.purchase = purchase;
module.exports.claimSeat = claimSeat;
module.exports.summarize = summarize;
module.exports.hasStore = hasStore;
module.exports.SEAT_PRICE_YUAN = SEAT_PRICE_YUAN;
module.exports.SEAT_PRICE_COIN = SEAT_PRICE_COIN;
module.exports.default = onRequest;
