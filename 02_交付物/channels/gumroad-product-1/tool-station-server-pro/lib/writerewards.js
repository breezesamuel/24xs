'use strict';
// writerewards.js - 写作赚币账本 (赚钱回路新维度: 内容创作得币)
// 语义: 用户投稿内容 (文章/文案/评测) -> 服务器 *服务端* 质量门禁 (长度/去重/关键词) -> 按质量记币。
// 原则 (诚实, 防刷):
//   - 服务端权威: 币额/质量 由服务器判, 客户端不能自报 "我写了 10000 字给我 100 币"
//   - 防刷: 同 ref 内容哈希去重 (重复投稿不重复给币), 单日上限 (max_per_day)
//   - fail-closed: 无存储 / 内容过短 / 重复 -> ok:false, 绝不假成功
//   - 不群发 / 不刷量: 纯被动 (用户主动投稿才记), 不主动制造内容
// 存储: 复用 cashback.js 同款 KV/Supabase + CN 文件回退 (key 前缀 wr:)
// Endpoints: /api/writerewards?action=summary|ledger|rate|settle
const TOKENS_PER_POST = (function () { var v = parseFloat(process.env.WRITEREWARD_TOKENS); return (isFinite(v) && v > 0) ? v : 10; })();
const MIN_WORDS = (function () { var v = parseInt(process.env.WRITEREWARD_MIN_WORDS, 10); return isFinite(v) && v > 0 ? v : 80; })();   // 最少字数 (中文按字符)
const MAX_PER_DAY = (function () { var v = parseInt(process.env.WRITEREWARD_MAX_PER_DAY, 10); return isFinite(v) && v > 0 ? v : 3; })();
var SETTLE_THRESHOLD = 100;   // 累计币达到才可提现
var ADMIN_SECRET = process.env.ADMIN_SECRET || process.env.AUTOOPS_SECRET || '';

function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
function fileStore() { try { var d = process.env.FILE_STORE_DIR; return (d && String(d).trim()) ? String(d).trim() : null; } catch (e) { return null; } }
function wrFilePath(key) { var dir = fileStore(); if (!dir) return null; var safe = String(key).replace(/[^A-Za-z0-9_.:-]/g, '_'); try { var path = require('path'); return path.join(dir, 'writerewards', safe + '.json'); } catch (e) { return null; } }
async function wrFileGet(key) { var p = wrFilePath(key); if (!p) return null; try { var fs = require('node:fs/promises'); return await fs.readFile(p, 'utf8'); } catch (e) { return null; } }
async function wrFileSet(key, val) { var p = wrFilePath(key); if (!p) return false; try { var fs = require('node:fs/promises'); var path = require('path'); await fs.mkdir(path.dirname(p), { recursive: true }); await fs.writeFile(p, val, 'utf8'); return true; } catch (e) { return false; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/writereward_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } } if (fileStore()) { var f = await wrFileGet(k); if (f !== null && f !== undefined) return f; } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (s) { try { var r = await fetch(s.u + '/rest/v1/writereward_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } catch (e) { } } if (fileStore() && await wrFileSet(k, v)) return true; return false; }
function hasStore() { return !!(kv() || up() || fileStore()); }

function keyOf(ref) { return 'wr:' + ref; }
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }
async function load(ref) { var raw = await dget(keyOf(ref)); if (!raw) return []; try { var a = JSON.parse(raw); return Array.isArray(a) ? a : []; } catch (e) { return []; } }
async function save(ref, arr) { return dset(keyOf(ref), JSON.stringify(arr)); }

// 内容质量门禁 (服务端): 去重 (FNV-1a 哈希), 字数, 反模板 (重复率)
function contentHash(s) { var h = 0x811c9dc5; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = (h * 0x01000193) >>> 0; } return h.toString(16); }
function quality(content) {
  var text = String(content || '').trim();
  var len = text.length;
  var h = contentHash(text);
  var reasons = [];
  if (len < MIN_WORDS) reasons.push('too_short(' + len + '<' + MIN_WORDS + ')');
  // 反模板: 单字重复率 > 60% 视为垃圾
  if (len > 0) {
    var freq = {}; for (var i = 0; i < len; i++) { var c = text[i]; freq[c] = (freq[c] || 0) + 1; }
    var maxF = 0; for (var ch in freq) maxF = Math.max(maxF, freq[ch]);
    if (maxF / len > 0.6) reasons.push('low_diversity');
  }
  var qualityOk = reasons.length === 0;
  // 币额: 基础 + 字数加成 (服务端定, 客户端不可伪造)
  var tokens = qualityOk ? Math.round(TOKENS_PER_POST + Math.min(50, Math.floor(len / 200))) : 0;
  return { ok: qualityOk, reasons: reasons, hash: h, len: len, tokens: tokens };
}

// record: 投稿一篇内容 -> 质量门禁 -> 记币。由 alipay.js 或前端投稿入口进程内调用。
async function record(ref, content, meta) {
  ref = String(ref || '').slice(0, 64);
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var q = quality(content);
  if (!q.ok) return { ok: false, error: 'rejected', reasons: q.reasons };
  var arr = await load(ref);
  // 去重: 同内容哈希已存在 -> duplicate 不给币
  for (var i = 0; i < arr.length; i++) { if (arr[i] && arr[i].hash === q.hash) return { ok: true, duplicate: true, entry: arr[i] }; }
  // 单日上限 (防刷)
  var today = new Date().toISOString().slice(0, 10);
  var todayCount = 0;
  for (var j = 0; j < arr.length; j++) { if (arr[j] && String(arr[j].day) === today && arr[j].status !== 'rejected') todayCount++; }
  if (todayCount >= MAX_PER_DAY) return { ok: false, error: 'daily_cap_reached', cap: MAX_PER_DAY };
  var entry = {
    id: 'WR' + Date.now().toString(36) + Math.floor(Math.random() * 1e6).toString(36),
    hash: q.hash,
    len: q.len,
    title: String((meta && meta.title) || '').slice(0, 80),
    tokens: q.tokens,
    day: today,
    at: Date.now(),
    status: 'pending'
  };
  arr.push(entry);
  var ok = await save(ref, arr);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, entry: entry, tokens_awarded: q.tokens };
}

function summarize(ref, arr) {
  var total = 0, pending = 0, settled = 0, n = 0, posts = 0;
  for (var i = 0; i < arr.length; i++) {
    var e = arr[i] || {};
    if (e.status === 'rejected') continue;
    if (e.status === 'settled') { settled += e.tokens || 0; n++; } else { pending += e.tokens || 0; posts++; }
    total += e.tokens || 0;
  }
  return {
    ref: ref, tokens_per_post_base: TOKENS_PER_POST, min_words: MIN_WORDS, max_per_day: MAX_PER_DAY, settle_threshold: SETTLE_THRESHOLD,
    posts: posts, settled_count: n,
    tokens_total: total, pending: pending, settled: settled,
    can_settle: total >= SETTLE_THRESHOLD && pending > 0
  };
}

async function settle(ref, meta) {
  if (!okRef(ref)) return { ok: false, error: 'missing_or_invalid_ref' };
  if (!hasStore()) return { ok: false, error: 'store_failed' };
  var arr = await load(ref);
  var sum = summarize(ref, arr);
  if (!sum.can_settle) return { ok: false, error: 'below_threshold_or_nothing_pending', pending: sum.pending, threshold: sum.settle_threshold };
  var cnt = 0, amt = 0;
  for (var i = 0; i < arr.length; i++) {
    var e = arr[i];
    if (!e || e.status === 'settled' || e.status === 'rejected') continue;
    e.status = 'settled'; e.settled_at = Date.now();
    if (meta && meta.method) e.method = String(meta.method).slice(0, 32);
    cnt++; amt += e.tokens || 0;
  }
  var ok = await save(ref, arr);
  if (!ok) return { ok: false, error: 'store_failed' };
  return { ok: true, settled_count: cnt, settled_tokens: amt };
}

async function onRequest(req, res, data) {
  var send = function (c, o) { try { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); } catch (e) { } };
  var p = String((data && data.path) || '').split('?')[0];
  var action = String((data && data.action) || '').slice(0, 24) || p.replace(/^\/api\/writerewards\/?/, '') || 'summary';
  var ref = String((data && data.ref) || '').slice(0, 64);
  if (action === 'rate') { return send(200, { ok: true, tokens_per_post: TOKENS_PER_POST, min_words: MIN_WORDS, max_per_day: MAX_PER_DAY, settle_threshold: SETTLE_THRESHOLD, store: hasStore() ? storeName() : 'none' }); }
  if (!okRef(ref)) return send(200, { ok: false, error: 'missing_or_invalid_ref' });
  try {
    if (action === 'summary') { var arr = await load(ref); return send(200, Object.assign({ ok: true, store: hasStore() ? storeName() : 'none' }, summarize(ref, arr))); }
    if (action === 'ledger' || action === 'list') { var arr2 = await load(ref); arr2.sort(function (a, b) { return (b.at || 0) - (a.at || 0); }); return send(200, { ok: true, count: arr2.length, entries: arr2.slice(0, 200) }); }
    if (action === 'settle') {
      var secret = String((data && (data.secret || data.key)) || (req.headers && (req.headers['x-admin-secret'] || req.headers['x-admin-key'])) || '');
      if (!ADMIN_SECRET || secret !== ADMIN_SECRET) return send(403, { ok: false, error: 'forbidden' });
      var r = await settle(ref, { method: data && data.method });
      return send(200, r);
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
module.exports.quality = quality;
module.exports.hasStore = hasStore;
module.exports.load = load;
module.exports.default = onRequest;
