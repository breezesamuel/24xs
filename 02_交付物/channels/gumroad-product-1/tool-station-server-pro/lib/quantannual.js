'use strict';
// quantannual.js - C12 合规渠道: 量化算力年费/包月订阅 (锁客, 持续进账, 最高客单价)
// 借鉴竞品真实收费结构:
//   - QuantConnect: 年付档 (Researcher/Team 年付比月付省) + 算力节点分档 + 白标
//   - Lovable: 按月订阅 + 团队共享池 + 年付周期
// 复用 C3~C11 同款存储原语 (KV/Supabase 双写 + CN 文件回退, key 前缀 qa:)
// 合规 (诚实 + fail-closed + 不造假):
//   - 服务端权威: 订阅有效期/算力额度 由服务端算, 客户端不可伪造
//   - 订阅 = 期内无限算力额度 (月付/年付), 到期自动停止 (fail-closed, 不永久白嫖)
//   - 合规免责: 算力输出基于历史数据, 非投资建议, 不代表未来
// 变现: 币走 coinsettle / ¥走支付宝; 购买 = 开通该 ref 的订阅有效期
// Endpoints: /api/quantannual?action=rate|summary|status|purchase|record
//   purchase/record 需 admin secret (防伪造付费)
const PRICE_MONTH_YUAN = (function () { var v = parseFloat(process.env.QA_MONTH_YUAN); return (isFinite(v) && v > 0) ? v : 399; })();
const PRICE_YEAR_YUAN = (function () { var v = parseFloat(process.env.QA_YEAR_YUAN); return (isFinite(v) && v > 0) ? v : 3990; })(); // 年付=12月9折, 锁客
const PRICE_MONTH_COIN = (function () { var v = parseFloat(process.env.QA_MONTH_COIN); return (isFinite(v) && v > 0) ? v : 4000; })();
const PRICE_YEAR_COIN = (function () { var v = parseFloat(process.env.QA_YEAR_COIN); return (isFinite(v) && v > 0) ? v : 39900; })();
const MONTH_MS = 30 * 24 * 3600 * 1000;
const ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
function fileStore() { try { var d = process.env.FILE_STORE_DIR; return (d && String(d).trim()) ? String(d).trim() : null; } catch (e) { return null; } }
function qaFilePath(key) { var dir = fileStore(); if (!dir) return null; var safe = String(key).replace(/[^A-Za-z0-9_.:-]/g, '_'); try { var p = require('path'); return p.join(dir, 'quantannual', safe + '.json'); } catch (e) { return null; } }
async function qaFileGet(key) { var p = qaFilePath(key); if (!p) return null; try { return await require('node:fs/promises').readFile(p, 'utf8'); } catch (e) { return null; } }
async function qaFileSet(key, val) { var p = qaFilePath(key); if (!p) return false; try { var fs = require('node:fs/promises'); var P = require('path'); await fs.mkdir(P.dirname(p), { recursive: true }); await fs.writeFile(p, val, 'utf8'); return true; } catch (e) { return false; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/quantannual_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } } if (fileStore()) { var f = await qaFileGet(k); if (f !== null && f !== undefined) return f; } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/quantannual_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } catch (e) { } } if (fileStore() && await qaFileSet(k, v)) return true; return false; }
function hasStore() { return !!(kv() || up() || fileStore()); }
function storeName() { return kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')); }
function keyOf(ref) { return 'qa:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return { active_until: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] }; try { var o = JSON.parse(raw); return o && typeof o === 'object' ? o : null; } catch (e) { return null; } }
async function save(ref, o) { return dset(keyOf(ref), JSON.stringify(o)); }

function complianceFooter() {
  return {
    disclaimer: '算力任务输出基于历史数据, 不构成投资建议, 亦不代表未来收益。数据来自公开行情源, 用户自行承担风险。订阅到期自动停止, 不永久白嫖。',
    data_source: 'public_market_data', generated_at: new Date().toISOString()
  };
}

// purchase: 开通订阅 (月付 1 月 / 年付 12 月, 期内无限算力额度)
async function purchase(ref, payload) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var outNo = String(payload.out_trade_no || ('coinsettle:' + Date.now())).slice(0, 80);
  var via = String(payload.paid_via || 'alipay').slice(0, 16);
  var cycle = String(payload.cycle || 'year').slice(0, 8); // month | year
  var isYear = (cycle === 'year' || cycle === 'annual');
  var priceYuan = isYear ? PRICE_YEAR_YUAN : PRICE_MONTH_YUAN;
  var priceCoin = isYear ? PRICE_YEAR_COIN : PRICE_MONTH_COIN;
  var durMs = isYear ? MONTH_MS * 12 : MONTH_MS;
  var st = await load(ref); if (!st) st = { active_until: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  for (var i = 0; i < st.entries.length; i++) { if (st.entries[i] && st.entries[i].out_trade_no === outNo) return { ok: true, duplicate: true, entry: st.entries[i] }; }
  var now = Date.now();
  // 在现有有效期基础上叠加 (续费), 否则从当前起
  var base = st.active_until > now ? st.active_until : now;
  st.active_until = base + durMs;
  st.entries.push({ id: 'QA' + now.toString(36) + Math.floor(Math.random() * 1e6).toString(36), out_trade_no: outNo, via: via, cycle: isYear ? 'year' : 'month', price_yuan: priceYuan, price_coin: priceCoin, status: 'active', at: now });
  if (via === 'alipay') st.revenue_yuan += priceYuan; else st.revenue_coin += priceCoin;
  var ok = await save(ref, st);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: st.entries[st.entries.length - 1], active_until: st.active_until, days_left: Math.round((st.active_until - now) / 86400000) };
}

function summarize(ref, st) {
  st = st || { active_until: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
  var now = Date.now();
  var active = st.active_until > now;
  return {
    ref: ref, active: active,
    active_until: st.active_until, days_left: active ? Math.round((st.active_until - now) / 86400000) : 0,
    month_price_yuan: PRICE_MONTH_YUAN, year_price_yuan: PRICE_YEAR_YUAN,
    month_price_coin: PRICE_MONTH_COIN, year_price_coin: PRICE_YEAR_COIN,
    revenue_yuan: st.revenue_yuan, revenue_coin: st.revenue_coin, entries_count: st.entries.length
  };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/quantannual\//, '') || 'rate';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') return send(200, { ok: true, month_price_yuan: PRICE_MONTH_YUAN, year_price_yuan: PRICE_YEAR_YUAN, month_price_coin: PRICE_MONTH_COIN, year_price_coin: PRICE_YEAR_COIN, store: hasStore() ? storeName() : 'none', note: '量化算力订阅 (月付/年付, 期内无限算力, 到期自动停); 输出基于历史数据, 非投资建议' });
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    var st = await load(ref); if (!st) st = { active_until: 0, revenue_yuan: 0, revenue_coin: 0, entries: [] };
    if (action === 'summary' || action === 'status') { return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, st))); }
    if (action === 'ledger' || action === 'list') { st.entries.sort(function (a, b) { return (b.at || 0) - (a.at || 0); }); return send(200, { ok: true, count: st.entries.length, entries: st.entries.slice(0, 100) }); }
    if (action === 'purchase' || action === 'record') {
      var secret = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden', note: 'purchase 需 admin secret (防客户端伪造付费)' });
      var r = await purchase(ref, data || {});
      return send(r.ok ? 200 : 400, r);
    }
    return send(404, { ok: false, error: 'no_route', action: action });
  } catch (e) { return send(500, { ok: false, error: 'exception', detail: String(e && e.message) }); }
}

module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.purchase = purchase;
module.exports.summarize = summarize;
module.exports.hasStore = hasStore;
module.exports.PRICE_MONTH_YUAN = PRICE_MONTH_YUAN;
module.exports.PRICE_YEAR_YUAN = PRICE_YEAR_YUAN;
module.exports.default = onRequest;
