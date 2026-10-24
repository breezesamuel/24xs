#!/usr/bin/env node
/**
 * rfm.mjs — B2B RFM 行为评分与分段（服务端权威、fail-closed、幂等）
 *
 * B2B 重定义的 RFM：
 *   R (Recency)  = 距最近触达/互动天数（越近越高分）
 *   F (Frequency)= 累计触达/互动次数（越多越高分）
 *   M (Monetary) = 累计定金/已付金额 + 预估潜在金额（越高越高分）
 *
 * 评分 1-5 分位（各维度独立）：
 *   5: 极优  4: 优  3: 中  2: 次  1: 差
 * 总分 = R*1 + F*1 + M*1（权重均等，满分 15）
 *
 * 5 段位（与佣金比例挂钩）：
 *   核心金牌 13-15 分 → 佣金 30%  / 高频深度触达
 *   潜力银牌 11-12 分 → 佣金 25%  / 中频精准触达
 *   铜牌      8-10 分  → 佣金 20%  / 标准触达
 *   培育      6-7  分  → 佣金 15%  / 低频培育
 *   流失      3-5  分  → 佣金 0%   / 仅低成本唤醒
 *
 * 存储：Vercel KV -> Supabase -> memory（fail-closed：无存储返回空/默认）
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const LEADS = path.join(ROOT, 'autoops/hidden/leads_auto.jsonl');
const CRM = path.join(ROOT, 'autoops/hidden/crm_auto.jsonl');
const ORDERS = path.join(ROOT, 'autoops/hidden/real_orders.jsonl');
const COMMISSION_KV_PREFIX = 'commission:';

const RFM_KV_PREFIX = 'rfm:';

// 存储抽象
function up() { try { var u = process.env.SUPABASE_URL, k = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY; return (u && k) ? { u: String(u).replace(/\/$/, ''), k: k } : null; } catch (e) { return null; } }
function kv() { try { var u = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL, t = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN; return (u && t) ? { u: String(u).replace(/\/$/, ''), t: t } : null; } catch (e) { return null; } }
async function kget(k) { try { var m = kv(); var r = m ? await fetch(m.u + '/get/' + encodeURIComponent(k), { headers: { Authorization: 'Bearer ' + m.t }, signal: AbortSignal.timeout(8000) }) : null; if (r) { var j = await r.json(); if (j && j.result !== null && j.result !== undefined) return j.result; } return null; } catch (e) { return null; } }
async function kset(k, v) { try { var m = kv(); if (m) { var body = (typeof v === 'string') ? v : JSON.stringify(v); var r = await fetch(m.u + '/set/' + encodeURIComponent(k), { method: 'POST', headers: { Authorization: 'Bearer ' + m.t, 'Content-Type': 'application/json' }, body: body, signal: AbortSignal.timeout(8000) }); if (r.ok) return true; } return false; } catch (e) { return false; } }
async function dget(k) { try { var v = await kget(k); if (v !== null && v !== undefined) return v; } catch (e) { } var s = up(); if (!s) return null; try { var r = await fetch(s.u + '/rest/v1/rfm_kv?k=eq.' + encodeURIComponent(k) + '&select=v', { headers: { apikey: s.k, Authorization: 'Bearer ' + s.k }, signal: AbortSignal.timeout(8000) }); var j = await r.json(); if (Array.isArray(j) && j[0]) return j[0].v; } catch (e) { } return null; }
async function dset(k, v) { if (await kset(k, v)) return true; var s = up(); if (!s) return false; try { var r = await fetch(s.u + '/rest/v1/rfm_kv', { method: 'POST', headers: { apikey: s.k, Authorization: 'Bearer ' + s.k, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=minimal' }, body: JSON.stringify([{ k: k, v: v }]), signal: AbortSignal.timeout(8000) }); return r.ok; } catch (e) { return false; } }
function hasStore() { return !!(kv() || up()); }

// 工具
function load(p) { if (!fs.existsSync(p)) return []; return fs.readFileSync(p, 'utf8').trim().split('\n').map(l => { try { return JSON.parse(l) } catch (e) { return null } }).filter(Boolean); }
function now() { return new Date().toISOString(); }
function daysAgo(ts) { if (!ts) return 9999; return Math.max(0, Math.floor((Date.now() - new Date(ts).getTime()) / 86400000)); }

// R 评分：距最近互动天数 → 1-5
function scoreR(days) {
  if (days <= 1) return 5;
  if (days <= 3) return 4;
  if (days <= 7) return 3;
  if (days <= 14) return 2;
  return 1;
}
// F 评分：累计触达次数 → 1-5
function scoreF(cnt) {
  if (cnt >= 10) return 5;
  if (cnt >= 5) return 4;
  if (cnt >= 3) return 3;
  if (cnt >= 2) return 2;
  return 1;
}
// M 评分：累计金额（元）+ 预估潜在金额 → 1-5
function scoreM(amountYuan) {
  if (amountYuan >= 1000) return 5;
  if (amountYuan >= 300) return 4;
  if (amountYuan >= 100) return 3;
  if (amountYuan >= 30) return 2;
  return 1;
}

// 段位定义
const TIERS = [
  { min: 13, max: 15, name: '核心金牌', label: 'GOLD', commissionPct: 30, touchFreq: 'daily', channels: ['wecom', 'tg', 'email'], priority: 'critical' },
  { min: 11, max: 12, name: '潜力银牌', label: 'SILVER', commissionPct: 25, touchFreq: 'daily', channels: ['tg', 'email'], priority: 'high' },
  { min: 8, max: 10, name: '铜牌', label: 'BRONZE', commissionPct: 20, touchFreq: '2d', channels: ['email'], priority: 'medium' },
  { min: 6, max: 7, name: '培育', label: 'NURTURE', commissionPct: 15, touchFreq: 'weekly', channels: ['email'], priority: 'low' },
  { min: 3, max: 5, name: '流失', label: 'CHURN', commissionPct: 0, touchFreq: 'monthly', channels: ['email'], priority: 'none' }
];

function tierOf(score) {
  for (const t of TIERS) { if (score >= t.min && score <= t.max) return t; }
  return TIERS[TIERS.length - 1];
}

async function loadLeads() { return load(LEADS); }
async function loadCRM() { return load(CRM); }
async function loadOrders() { return load(ORDERS); }
async function loadCommission(ref) {
  const data = await dget(COMMISSION_KV_PREFIX + ref);
  if (!data) return [];
  try { return JSON.parse(data); } catch (e) { return []; }
}

// 计算单个 ref 的 RFM
async function computeRFM(ref) {
  const leads = await loadLeads();
  const crm = await loadCRM();
  const orders = await loadOrders();
  const comm = await loadCommission(ref);

  // R: 最近互动天数 —— 取 CRM timeline + leads contacted + orders paid_at 的最小值
  let lastTouch = null;
  const crmRec = crm.find(c => c.lead_id === ref || c.url?.includes(ref));
  if (crmRec?.timeline?.length) {
    const ts = crmRec.timeline[crmRec.timeline.length - 1]?.ts;
    if (ts) lastTouch = ts;
  }
  const leadRec = leads.find(l => l.id === ref || l.url?.includes(ref));
  if (leadRec?.last_outreach_at) {
    if (!lastTouch || new Date(leadRec.last_outreach_at) > new Date(lastTouch)) lastTouch = leadRec.last_outreach_at;
  }
  const paidOrder = orders.find(o => o.ref === ref && o.paid);
  if (paidOrder?.paid_at) {
    if (!lastTouch || new Date(paidOrder.paid_at) > new Date(lastTouch)) lastTouch = paidOrder.paid_at;
  }
  const R = scoreR(lastTouch ? daysAgo(lastTouch) : 9999);

  // F: 触达次数 —— CRM timeline auto_* 计数 + leads.outreach_attempts + commission entries
  let freq = 0;
  if (crmRec?.timeline) freq += crmRec.timeline.filter(e => e.act?.startsWith('auto_')).length;
  if (leadRec?.outreach_attempts) freq += leadRec.outreach_attempts;
  const commList = await loadCommission(ref);
  freq += commList.length;
  const F = scoreF(freq);

  // M: 金额 —— 已付订单金额 + 佣金总额（作为潜在价值代理）
  let m = 0;
  if (paidOrder) m += parseFloat(paidOrder.amount || 0);
  const commAgg = await loadCommission(ref);
  for (const e of commAgg) m += parseFloat(e.commission || 0);
  // 预估潜在：基于 lead_score * 10（简易代理）
  const leadScore = leadRec?.lead_score || 0;
  m += leadScore * 10;
  const M = scoreM(m);

  const total = R + F + M;
  const tier = tierOf(total);

  return {
    ref,
    R, F, M, total,
    tier: tier.name,
    tierLabel: tier.label,
    commissionPct: tier.commissionPct,
    touchFreq: tier.touchFreq,
    channels: tier.channels,
    priority: tier.priority,
    details: { R, F, M, lastTouch, freq, monetary: m },
    updated_at: now()
  };
}

// 批量计算并写回 KV（按需触发）
async function computeAll() {
  if (!hasStore()) return { ok: false, error: 'no_store', count: 0 };
  const leads = await loadLeads();
  const seen = new Set();
  const uniqRefs = leads.map(l => l.id || l.url).filter(x => x && !seen.has(x) && !seen.add(x));
  let ok = 0;
  for (const ref of uniqRefs) {
    const rfm = await computeRFM(ref);
    const okSave = await dset(RFM_KV_PREFIX + ref, JSON.stringify(rfm));
    if (okSave) ok++;
    await new Promise(r => setTimeout(r, 50));
  }
  return { ok: true, count: ok };
}

// 单 ref 查询（含缓存）
async function getRFM(ref) {
  if (!okRef(ref)) return { ok: false, error: 'invalid_ref' };
  const cached = await dget(RFM_KV_PREFIX + ref);
  if (cached) {
    try { return { ok: true, cached: true, ...JSON.parse(cached) }; } catch (e) { }
  }
  return { ok: true, cached: false, ...await computeRFM(ref) };
}

// 批量查询（用于外联排程）
async function getAllRFM() {
  const leads = await loadLeads();
  const seen = new Set();
  const uniqRefs = leads.map(l => l.id || l.url).filter(x => x && !seen.has(x) && !seen.add(x));
  const out = [];
  for (const ref of uniqRefs) {
    const rfm = await getRFM(ref);
    if (rfm.ok) out.push(rfm);
    await new Promise(r => setTimeout(r, 10));
  }
  return out;
}

// 根据分段返回触达计划
function getTouchPlan(rfm) {
  const t = tierOf(rfm.total);
  return {
    tier: t.name,
    frequency: t.touchFreq,
    channels: t.channels,
    commissionPct: t.commissionPct,
    priority: t.priority,
    nextTouchInDays: t.touchFreq === 'daily' ? 1 : (t.touchFreq === '2d' ? 2 : (t.touchFreq === 'weekly' ? 7 : 30))
  };
}

// 导出：供 outreach / followup / crm 调用
function okRef(ref) { return /^[A-Za-z0-9_.-]{1,64}$/.test(String(ref || '')); }

export { computeRFM, computeAll, getRFM, getAllRFM, tierOf, getTouchPlan, TIERS, scoreR, scoreF, scoreM, okRef };
export default { computeRFM, computeAll, getRFM, getAllRFM, tierOf, getTouchPlan, TIERS, okRef };