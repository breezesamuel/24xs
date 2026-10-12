#!/usr/bin/env node
/**
 * hidden_outreach.mjs — 自动外联（RFM 分段感知）
 * - 按 RFM 分段动态决定：单轮配额、重试间隔、投递渠道优先级、优先级
 * - 诚实记录：无真实投递渠道时仅生成草稿，不标记 contacted
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { episodic, recall, conversation } from '../brain/hidden_brain.mjs';
import { getRFM, getTouchPlan, tierOf } from './rfm.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const LEADS = path.join(H, 'leads_auto.jsonl');
const DRAFTS = path.join(H, 'drafts_auto.jsonl');
const SENT = path.join(H, 'outreach_sent_auto.jsonl');
const CRM = path.join(H, 'crm_auto.jsonl');

function load(p) { if (!fs.existsSync(p)) return []; return fs.readFileSync(p, 'utf8').trim().split('\n').map(l => { try { return JSON.parse(l) } catch (e) { return null } }).filter(Boolean); }
function append(p, o) { fs.appendFileSync(p, JSON.stringify(o) + '\n'); }
function save(p, arr) { fs.writeFileSync(p, arr.map(x => JSON.stringify(x)).join('\n') + (arr.length ? '\n' : '')); }
function now() { return new Date().toISOString(); }

const BASE_MAX_PER_TICK = 3;
const BASE_RETRY_DELAY_MS = 30 * 60 * 1000;

function tierParams(rfm) {
  const plan = rfm ? (rfm.touchFreq || rfm.frequency) : 'weekly';
  const tier = rfm?.tier || '流失';
  const planMap = {
    daily: { maxPerTick: 6, retryMs: 15 * 60 * 1000, channels: ['wecom', 'tg', 'email'] },
    '2d': { maxPerTick: 4, retryMs: 30 * 60 * 1000, channels: ['tg', 'email'] },
    weekly: { maxPerTick: 2, retryMs: 2 * 60 * 60 * 1000, channels: ['email'] },
    monthly: { maxPerTick: 1, retryMs: 24 * 60 * 60 * 1000, channels: ['email'] }
  };
  const p = planMap[plan] || planMap.weekly;
  return { maxPerTick: p.maxPerTick, retryMs: p.retryMs, channels: p.channels, tier };
}

function canRetry(lead, retryMs) {
  if (!lead.last_outreach_at) return true;
  return Date.now() - new Date(lead.last_outreach_at).getTime() >= retryMs;
}

async function ai(prompt) {
  const key = process.env.OPENROUTER_API_KEY || process.env.AI_API_KEY || '';
  const base = process.env.AI_BASE_URL || 'https://openrouter.ai/api/v1/chat/completions';
  const model = process.env.AI_MODEL || 'deepseek/deepseek-chat-v3-0324:free';
  if (!key) return { ok: false, reason: 'no_key', retryable: true };
  try {
    const res = await fetch(base, {
      method: 'POST', headers: { 'Authorization': `Bearer ${key}`, 'Content-Type': 'application/json', 'HTTP-Referer': 'https://app.highkingflower.com', 'X-Title': '24XS-Hidden-Outreach' },
      body: JSON.stringify({ model: process.env.AI_MODEL || 'deepseek/deepseek-chat-v3-0324:free', temperature: 0.22, max_tokens: 240, messages: [{ role: 'system', content: '你是全自动商务助理。生成极简、合规的首次沟通话术（<=32字）。不夸大、不承诺、不敏感用语。' }, { role: 'user', content: prompt }] })
    });
    if (!res.ok) { const retryable = res.status === 429 || res.status >= 500; return { ok: false, reason: `http_${res.status}`, retryable }; }
    const j = await res.json();
    const txt = j.choices?.[0]?.message?.content?.trim().replace(/\s+/g, ' ');
    return { ok: true, text: txt.slice(0, 120) };
  } catch (e) { return { ok: false, reason: e.message, retryable: true }; }
}

async function main() {
  const { getRFM } = await import('./rfm.mjs');
  const allLeads = load(LEADS);
  const leadsWithRFM = [];
  for (const l of allLeads) {
    const rfm = await getRFM(l.id || l.url);
    const tier = rfm.ok ? (rfm.tier || '流失') : '流失';
    leadsWithRFM.push({ lead: l, rfm: rfm.ok ? rfm : null, tier, priority: rfm.ok ? (rfm.priority || 'low') : 'low' });
  }
  const prioOrder = { critical: 5, high: 4, medium: 3, low: 2, none: 1 };
  leadsWithRFM.sort((a, b) => (prioOrder[b.priority] || 1) - (prioOrder[a.priority] || 1));

  const candidates = leadsWithRFM.filter(x => {
    const l = x.lead;
    return (l.stage === 'discovered' || (l.stage === 'outreach_failed' && canRetry(l, x.rfm?.retryMs || BASE_RETRY_DELAY_MS))) && !l.contacted;
  });

  const batch = [];
  const tierCounts = { '核心金牌': 0, '潜力银牌': 0, '铜牌': 0, '培育': 0, '流失': 0 };
  for (const x of candidates) {
    const tier = x.tier;
    const params = tierParams(x.rfm);
    if (tierCounts[tier] < params.maxPerTick) {
      batch.push(x);
      tierCounts[tier]++;
    }
    if (batch.length >= 8) break;
  }

  const kn = recall('knowledge', 10).map(k => k.rule).join(' | ');
  let d = 0, s = 0, deferred = 0;
  const allLeadsArr = load(LEADS);

  for (const x of batch) {
    const l = x.lead;
    const params = tierParams(x.rfm);
    const prompt = `历史经验：${kn || '无'}\n线索：${l.url}\n分段：${x.tier}（渠道：${params.channels.join(',')}）\n请生成一条合规首次话术（<=32字），仅谈可能价值。只返回话术。`;
    const r = await ai(prompt);
    const ts = now();

    const dr = { id: `HD-${Date.now()}-${d}`, lead_id: l.id, url: l.url, ai_ok: r.ok, text: r.ok ? r.text : '', auto: true, sent: r.ok, sent_at: r.ok ? ts : undefined, created_at: ts, retryable: r.retryable, tier: x.tier, channels: params.channels };
    append(DRAFTS, dr);

    const idx = allLeadsArr.findIndex(y => y.id === l.id);
    if (idx >= 0) {
      allLeadsArr[idx].last_outreach_at = ts;
      allLeadsArr[idx].outreach_attempts = (allLeadsArr[idx].outreach_attempts || 0) + 1;
      allLeadsArr[idx].rfm_tier = x.tier;
      allLeadsArr[idx].rfm_priority = x.priority;

      if (r.ok) {
        conversation(l.id, 'auto_outreach', dr.text);
        append(SENT, { sid: `HS-${Date.now()}-${s++}`, lead_id: l.id, text: dr.text, channel: params.channels[0] || 'none', status: 'drafted', auto: true, drafted_at: ts, note: '无真实投递渠道，仅生成草稿', tier: x.tier });
        const crm = load(CRM);
        let rec = crm.find(y => y.lead_id === l.id);
        if (!rec) {
          rec = { crm_id: `HCRM-${Date.now()}-${d}`, lead_id: l.id, url: l.url, stage: 'drafted', owner: 'hidden_auto', priority: x.priority, tier: x.tier, channels: params.channels, timeline: [], auto: true, created_at: ts, updated_at: ts };
          crm.push(rec);
        }
        rec.stage = 'drafted'; rec.priority = x.priority; rec.tier = x.tier; rec.channels = params.channels;
        rec.timeline.push({ ts, act: 'auto_drafted', note: `生成外呼草稿（分段：${x.tier}，渠道：${params.channels.join(',')}，无真实投递渠道）` }); rec.updated_at = ts; save(CRM, crm);
        d++; s++;
      } else {
        if (r.retryable && allLeadsArr[idx].outreach_attempts < 5) {
          allLeadsArr[idx].stage = 'discovered';
          deferred++;
        } else {
          allLeadsArr[idx].stage = 'outreach_failed';
        }
      }
    }
    d++;
    await new Promise(r => setTimeout(r, 1500));
  }

  save(LEADS, allLeadsArr);
  episodic('hidden_outreach_auto', { drafted: d, sent: 0, deferred, total_pending: candidates.length, note: 'sent=0 因无真实投递渠道', tierCounts });
  console.log(`[hidden_outreach] ${d} processed, 0 sent (no delivery channel), ${deferred} deferred, tiers:`, tierCounts);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) { main(); }