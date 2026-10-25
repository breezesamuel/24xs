'use strict';
// track.js - 第一方统计（PV / 来源 / 工具使用 / 事件），存 Vercel KV -> Supabase -> 无
// 用途: 1) 让"有没有流量、哪些页在转化"可观测（之前站内 0 统计，运营是瞎的）
//       2) 喂给自动核账与 REPORT.md 的漏斗数据
// 端点: POST /api/track  (beacon)  |  GET /api/track?days=7  (汇总)
const DAY_MS = 86400000;

function kv() {
  try {
    const u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
    const t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
    return (u && t) ? { u: String(u).replace(/\/$/, ''), t } : null;
  } catch (e) { return null; }
}
function up() {
  try {
    const u = process.env.SUPABASE_URL;
    const k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;
    return (u && k) ? { u: String(u).replace(/\/$/, ''), k } : null;
  } catch (e) { return null; }
}
async function kget(key) {
  const m = kv();
  if (m) {
    try {
      const r = await fetch(m.u + '/get/' + encodeURIComponent(key), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(6000) });
      const j = await r.json();
      return (j && j.result !== null && j.result !== undefined) ? JSON.parse(j.result) : null;
    } catch (e) { /* 落到文件存储 */ }
  }
  if (fileStore()) {
    const v = await fileGet(key);
    if (v !== null && v !== undefined) return v;
  }
  return null;
}
async function kset(key, val) {
  const m = kv();
  if (m) {
    try {
      const body = (typeof val === 'string') ? val : JSON.stringify(val);
      const r = await fetch(m.u + '/set/' + encodeURIComponent(key), {
        method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' },
        body, signal: AbortSignal.timeout(6000)
      });
      if (r.ok) return true;
    } catch (e) { /* 落到文件存储 */ }
  }
  if (fileStore()) return await fileSet(key, val);
  return false;
}
function dayKey(ts) {
  return 'track_' + new Date(ts || Date.now()).toISOString().slice(0, 10).replace(/-/g, '');
}

// 文件存储回退：自托管实例（无 KV）也能持久化统计数据。
// 与 alipay.js 同一套约定：仅在设置了 FILE_STORE_DIR 且无远端存储时启用。
function fileStore() {
  try {
    const d = process.env.FILE_STORE_DIR;
    return (d && String(d).trim()) ? String(d).trim() : null;
  } catch (e) { return null; }
}
function filePath(key) {
  const dir = fileStore(); if (!dir) return null;
  const safe = String(key).replace(/[^A-Za-z0-9_.-]/g, '_').slice(0, 180);
  return dir + '/' + safe + '.json';
}
async function fileGet(key) {
  const p = filePath(key); if (!p) return null;
  try {
    const fs = require('node:fs/promises');
    return JSON.parse(await fs.readFile(p, 'utf8'));
  } catch (e) { return null; }
}
async function fileSet(key, val) {
  const p = filePath(key); if (!p) return false;
  try {
    const fs = require('node:fs/promises');
    await fs.mkdir(fileStore(), { recursive: true });
    const tmp = p + '.tmp';
    await fs.writeFile(tmp, JSON.stringify(val), 'utf8');
    await fs.rename(tmp, p);
    return true;
  } catch (e) { return false; }
}
function hostOf(ref) {
  if (!ref) return 'direct';
  try { return new URL(ref).hostname || 'direct'; } catch (e) { return 'other'; }
}

async function record(payload) {
  const ts = Number(payload.t) || Date.now();
  const key = dayKey(ts);
  const cur = (await kget(key)) || {};
  const path = String(payload.p || '/').slice(0, 120);
  const ev = String(payload.e || 'pv').slice(0, 24);
  const src = hostOf(payload.r);
  cur.pv = (cur.pv || 0) + (ev === 'pv' ? 1 : 0);
  cur.events = (cur.events || 0) + 1;
  cur.pages = cur.pages || {};
  cur.pages[path] = (cur.pages[path] || 0) + 1;
  cur.sources = cur.sources || {};
  cur.sources[src] = (cur.sources[src] || 0) + 1;
  cur.ev = cur.ev || {};
  cur.ev[ev] = (cur.ev[ev] || 0) + 1;
  // 保留最近 3 天（KV 是内存态，裁剪避免无限膨胀）
  const days = Object.keys(cur).filter(k => k.startsWith('day_'));
  if (days.length > 3) { for (const d of days) delete cur[d]; }
  cur.day = key;
  const ok = await kset(key, cur);
  return { ok, store: kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')) };
}

async function summary(days) {
  const n = Math.max(1, Math.min(30, days || 7));
  const out = [];
  for (let i = 0; i < n; i++) {
    const k = dayKey(Date.now() - i * DAY_MS);
    const d = await kget(k);
    if (d) out.push({ day: k, ...d });
  }
  const pages = {}, sources = {}, ev = {};
  let pv = 0, events = 0;
  for (const d of out) {
    pv += d.pv || 0; events += d.events || 0;
    for (const p in (d.pages || {})) pages[p] = (pages[p] || 0) + d.pages[p];
    for (const s in (d.sources || {})) sources[s] = (sources[s] || 0) + d.sources[s];
    for (const e in (d.ev || {})) ev[e] = (ev[e] || 0) + d.ev[e];
  }
  const top = (o) => Object.entries(o).sort((a, b) => b[1] - a[1]).slice(0, 20);
  return { days: n, pv, events, top_pages: top(pages), top_sources: top(sources), events_breakdown: ev, days_detail: out };
}

async function onRequest(req, res, data) {
  const send = (c, o) => { res.writeHead(c, { 'Content-Type': 'application/json;charset=utf-8' }); res.end(JSON.stringify(o)); };
  try {
    const method = (req && req.method) || 'GET';
    if (method === 'POST') {
      // Vercel Node 运行时把 body 放在 req.body；Pages 风格才用第三个参数 data
      const p = Object.assign({}, data || (req && req.body) || {});
      const r = await record(p);
      return send(200, { ok: true, store: r.store });
    }
    const days = data && data.days ? parseInt(data.days, 10) : 7;
    return send(200, Object.assign({ ok: true, store: kv() ? 'kv' : (up() ? 'supabase' : (fileStore() ? 'file' : 'none')) }, await summary(days)));
  } catch (e) {
    return send(200, { ok: false, error: String(e && e.message || e) });
  }
}
// ⚠️ 导出形态很关键: Vercel 的 @vercel/node 要求 `module.exports` 本身是**函数**
//    （早先导出对象 {onRequest,record,summary} → 线上 500 FUNCTION_INVOCATION_FAILED）。
//    现在导出函数本体，同时把具名成员挂上去，两种调用方式都能用。
module.exports = onRequest;
module.exports.onRequest = onRequest;
module.exports.record = record;
module.exports.summary = summary;
module.exports.default = onRequest;
