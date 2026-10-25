'use strict';
// commission.js - partner commission ledger (independent serverless module)
// Principles: server-authoritative (rate/earnings computed server-side, client cannot forge);
//             fail-closed (no store / bad ref -> ok:false, never fake success);
//             idempotent (one commission entry per paid out_trade_no);
//             ASCII-only source + \u escapes.
// Endpoints: /api/commission?action=summary|ledger|rate|settle  (also REST: /api/commission/summary)
// Storage: Vercel KV (kv rest) -> Supabase -> none (reads return empty, writes fail-closed)
// Note: record() is invoked in-process by alipay.js on verified payment success; it is NOT exposed
//       as a public HTTP action, so entries cannot be fabricated through the API.
const DEFAULT_RATE = (function () {
  var v = parseFloat(process.env.COMMISSION_PCT);
  return (isFinite(v) && v >= 0 && v <= 100) ? v : 30;
})();
var ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (!s) return null; try { var r = await fetch(s.u + '/rest/v1/commission_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (!s) return false; try { var r = await fetch(s.u + '/rest/v1/commission_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); return r.ok; } catch (e) { return false; } }
function hasStore() { return !!(kv() || up()); }

function keyOf(ref) { return 'commission:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return []; try { var a = JSON.parse(raw); return Array.isArray(a) ? a : []; } catch (e) { return []; } }
async function save(ref, arr) { return dset(keyOf(ref), JSON.stringify(arr)); }
function cents(x) { var n = parseFloat(x); if (!isFinite(n) || n < 0) return 0; return Math.round(n * 100); }
function yuan(c) { return (c / 100); }

// record a commission for the referrer of a paid order (idempotent by out_trade_no)
async function record(ref, order) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!order || !order.out_trade_no) return { ok: false, error: 'missing_order' };
  var outNo = String(order.out_trade_no).slice(0, 64);
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var arr = await load(ref);
  for (var i = 0; i < arr.length; i++) { if (arr[i] && arr[i].out_trade_no === outNo) return { ok: true, duplicate: true, entry: arr[i] }; }
  var amountC = cents(order.amount);
  if (amountC <= 0) return { ok: false, error: 'invalid_amount' };
  var rate = DEFAULT_RATE;
  var commC = Math.round(amountC * rate / 100);
  var entry = {
    id: 'C' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36),
    out_trade_no: outNo,
    amount: yuan(amountC),
    kind: String(order.kind || 'unlock').slice(0, 16),
    plan: String(order.plan || '').slice(0, 24),
    rate: rate,
    commission: yuan(commC),
    at: Date.now(),
    status: 'pending'
  };
  arr.push(entry);
  var ok = await save(ref, arr);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: entry };
}

function summarize(ref, arr) {
  var grossC = 0, commC = 0, pendingC = 0, settledC = 0, settledN = 0;
  for (var i = 0; i < arr.length; i++) {
    var e = arr[i] || {};
    grossC += cents(e.amount);
    var c = cents(e.commission); commC += c;
    if (e.status === 'settled') { settledC += c; settledN++; } else { pendingC += c; }
  }
  return {
    ref: ref, rate: DEFAULT_RATE,
    count: arr.length, settled_count: settledN,
    gross: yuan(grossC), commission_total: yuan(commC),
    pending: yuan(pendingC), settled: yuan(settledC)
  };
}

// settle: mark entries as settled (admin only, fail-closed without matching secret)
async function settle(ref, ids, meta) {
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var arr = await load(ref);
  var target = (ids && ids.length) ? ids : null;
  var n = 0, sumC = 0;
  for (var i = 0; i < arr.length; i++) {
    var e = arr[i];
    if (!e || e.status === 'settled') continue;
    if (target && target.indexOf(e.id) < 0 && target.indexOf(e.out_trade_no) < 0) continue;
    e.status = 'settled'; e.settled_at = Date.now();
    if (meta && meta.txid) e.txid = String(meta.txid).slice(0, 128);
    if (meta && meta.method) e.method = String(meta.method).slice(0, 32);
    n++; sumC += cents(e.commission);
  }
  var ok = await save(ref, arr);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, settled_count: n, settled_amount: yuan(sumC) };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/commission\/?/, '') || 'summary';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') { return send(200, { ok: true, rate: DEFAULT_RATE, store: hasStore() ? storeName() : 'none' }); }
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    if (action === 'summary') {
      var arr = await load(ref);
      return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, arr)));
    }
    if (action === 'ledger' || action === 'list') {
      var arr2 = await load(ref);
      arr2.sort(function (a, b) { return (b.at || 0) - (a.at || 0); });
      return send(200, { ok: true, count: arr2.length, entries: arr2.slice(0, 200) });
    }
    if (action === 'settle') {
      var secret = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden' });
      var ids = String((data && data.ids) || '').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
      var r = await settle(ref, ids, { txid: data && data.txid, method: data && data.method });
      return send(200, r);
    }
    return send(404, { ok: false, error: 'no_route', action: action });
  } catch (e) {
    return send(500, { ok: false, error: 'exception', detail: String(e && e.message) });
  }
}
function storeName() { return kv() ? 'kv' : (up() ? 'supabase' : 'none'); }

module.exports = { onRequest: onRequest, record: record, settle: settle, summarize: summarize, load: load, rate: function () { return DEFAULT_RATE; }, storeName: storeName };
