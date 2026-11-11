'use strict';
// cashback.js - 购物返现账本 (赚钱回路新维度: 购物返现)
// 复用 commission.js 的存储原语 (KV REST -> Supabase 双写), 但语义是:
//   用户 *自己* 通过我们的链接购物/消费, 按比例返现到其账本 (affiliate cashback)。
// 原则 (与 commission.js 一致, 诚实):
//   - 服务器权威: 返现比例/金额 服务端算, 客户端不可伪造
//   - fail-closed: 无存储 / ref 非法 / 金额<=0 -> ok:false, 绝不假成功
//   - 幂等: 每个 out_trade_no 只记一条 (重复调用返回 duplicate)
//   - 只在 *验证过的* 支付成功 时由 alipay.js 进程内调用 record(), 不暴露公开写端点
// Endpoints: /api/cashback?action=summary|ledger|rate|settle  (只读 + settle 需 admin secret)
const CASHBACK_PCT = (function () {
  var v = parseFloat(process.env.CASHBACK_PCT);
  return (isFinite(v) && v >= 0 && v <= 100) ? v : 5;   // 默认 5% 返现
})();
// 提现门槛 (达到才可 settle -> 支付宝付款)
var SETTLE_THRESHOLD_YUAN = 10;
var ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

// ---- 存储 (KV/Supabase 双写 + CN 文件回退 FILE_STORE_DIR, 独立 key 前缀 cbk:) ----
function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
function fileStore() { try { var d = process.env.FILE_STORE_DIR; return (d && String(d).trim()) ? String(d).trim() : null; } catch (e) { return null; } }
function cbFilePath(key) { var dir = fileStore(); if (!dir) return null; var safe = String(key).replace(/[^A-Za-z0-9_.:-]/g, '_'); try { var path = require('path'); return path.join(dir, 'cashback', safe + '.json'); } catch (e) { return null; } }
async function cbFileGet(key) { var p = cbFilePath(key); if (!p) return null; try { var fs = require('node:fs/promises'); return await fs.readFile(p, 'utf8'); } catch (e) { return null; } }
async function cbFileSet(key, val) { var p = cbFilePath(key); if (!p) return false; try { var fs = require('node:fs/promises'); var path = require('path'); await fs.mkdir(path.dirname(p), { recursive: true }); await fs.writeFile(p, val, 'utf8'); return true; } catch (e) { return false; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/cashback_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } } if (fileStore()) { var f = await cbFileGet(k); if (f !== null && f !== undefined) return f; } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/cashback_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } catch (e) { } } if (fileStore() && await cbFileSet(k, v)) return true; return false; }
function hasStore() { return !!(kv() || up() || fileStore()); }

function keyOf(ref) { return 'cbk:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return []; try { var a = JSON.parse(raw); return Array.isArray(a) ? a : []; } catch (e) { return []; } }
async function save(ref, arr) { return dset(keyOf(ref), JSON.stringify(arr)); }
function cents(x) { var n = parseFloat(x); if (!isFinite(n) || n < 0) return 0; return Math.round(n * 100); }
function yuan(c) { return (c / 100); }

// record: 为 "自己购物" 的付费订单记返现 (幂等 by out_trade_no)。由 alipay.js 验证成功后调用。
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
  var cbC = Math.round(amountC * CASHBACK_PCT / 100);
  var entry = {
    id: 'CBK' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36),
    out_trade_no: outNo,
    purchase: yuan(amountC),
    rate: CASHBACK_PCT,
    cashback: yuan(cbC),
    merchant: String(order.merchant || 'self').slice(0, 32),
    kind: String(order.kind || 'shopping').slice(0, 16),
    at: Date.now(),
    status: 'pending'
  };
  arr.push(entry);
  var ok = await save(ref, arr);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: entry };
}

function summarize(ref, arr) {
  var grossC = 0, cbC = 0, pendingC = 0, settledC = 0, settledN = 0;
  for (var i = 0; i < arr.length; i++) {
    var e = arr[i] || {};
    grossC += cents(e.purchase);
    var c = cents(e.cashback); cbC += c;
    if (e.status === 'settled') { settledC += c; settledN++; } else { pendingC += c; }
  }
  var total = yuan(cbC);
  return {
    ref: ref, rate_pct: CASHBACK_PCT, settle_threshold_yuan: SETTLE_THRESHOLD_YUAN,
    count: arr.length, settled_count: settledN,
    purchase_gross: yuan(grossC), cashback_total: total,
    pending: yuan(pendingC), settled: yuan(settledC),
    can_settle: total >= SETTLE_THRESHOLD_YUAN && cbC > 0 && settledC < cbC
  };
}

// settle: 标记可提现返现为已结算 (admin only, fail-closed; 需达到门槛)
async function settle(ref, meta) {
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var arr = await load(ref);
  var sum = summarize(ref, arr);
  if (!sum.can_settle) return { ok: false, error: 'below_threshold_or_nothing_pending', pending: sum.pending, threshold: sum.settle_threshold_yuan };
  var n = 0, sumC = 0;
  for (var i = 0; i < arr.length; i++) {
    var e = arr[i];
    if (!e || e.status === 'settled') continue;
    e.status = 'settled'; e.settled_at = Date.now();
    if (meta && meta.txid) e.txid = String(meta.txid).slice(0, 128);
    if (meta && meta.method) e.method = String(meta.method).slice(0, 32);
    n++; sumC += cents(e.cashback);
  }
  var ok = await save(ref, arr);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, settled_count: n, settled_amount: yuan(sumC) };
}

// payout: 创建 "返现提现请求" (admin only, fail-closed)。
// 诚实原则: 只生成 *待人工确认* 的提现请求 (指向已配置 crypto 钱包), 不静默转账。
// 真实打款需 owner 持钱包私钥 + 合规确认 (Alipay fund.trans 转账 API 受商户权限限制)。
async function payout(ref, meta) {
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var arr = await load(ref);
  var sum = summarize(ref, arr);
  if (!sum.can_settle) return { ok: false, error: 'below_threshold', pending: sum.pending, threshold: sum.settle_threshold_yuan };
  var pendingC = cents(sum.pending);
  var wallet = String((meta && meta.wallet) || process.env.CASHBACK_PAYOUT_WALLET || 'payout_usdc').slice(0, 32);
  // 生成提现请求记录 (status=pending, 待 owner 人工打款后置 done)
  var req = {
    id: 'PO' + Date.now().toString(36),
    ref: ref,
    amount: yuan(pendingC),
    wallet: wallet,
    asset: 'USDC',
    status: 'pending',   // pending -> (owner 打款) -> done
    requested_at: Date.now(),
    note: 'cashback payout request; owner must confirm transfer (compliance)'
  };
  // 追加到独立 payout 请求账本 (按 ref 聚合)
  var pk = 'cbk_payouts:' + ref;
  var parrRaw = await dget(pk);
  var parr = [];
  try { parr = JSON.parse(parrRaw); if (!Array.isArray(parr)) parr = []; } catch (e) { parr = []; }
  parr.push(req);
  var ok = await dset(pk, JSON.stringify(parr));
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, payout_request: req, note: '生成待确认提现请求; 实际打款需 owner 人工 + 合规' };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/cashback\/?/, '') || 'summary';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') { return send(200, { ok: true, rate_pct: CASHBACK_PCT, settle_threshold_yuan: SETTLE_THRESHOLD_YUAN, store: hasStore() ? storeName() : 'none' }); }
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    if (action === 'summary') { var arr = await load(ref); return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, arr))); }
    if (action === 'ledger' || action === 'list') { var arr2 = await load(ref); arr2.sort(function (a, b) { return (b.at || 0) - (a.at || 0); }); return send(200, { ok: true, count: arr2.length, entries: arr2.slice(0, 200) }); }
    if (action === 'settle') {
      var secret = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden' });
      var r = await settle(ref, { txid: data && data.txid, method: data && data.method });
      return send(200, r);
    }
    if (action === 'payout') {
      var secret2 = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret2 !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden' });
      var r2 = await payout(ref, { wallet: data && data.wallet });
      return send(200, r2);
    }
    return send(404, { ok: false, error: 'no_route', action: action });
  } catch (e) { return send(500, { ok: false, error: 'exception', detail: String(e && e.message) }); }
}
function storeName() { return kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')); }

module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.record = record;
module.exports.summarize = summarize;
module.exports.settle = settle;
module.exports.payout = payout;
module.exports.hasStore = hasStore;
module.exports.load = load;
module.exports.default = onRequest;
