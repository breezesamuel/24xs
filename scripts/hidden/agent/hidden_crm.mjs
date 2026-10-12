#!/usr/bin/env node
/**
 * hidden_crm.mjs — CRM 阶段推进（RFM 分段感知）
 * - 分段差异化阶段延迟：高分段推进更快
 * - 佣金比例写入 CRM，供结算参考
 * - 不自动生成订单（真实单由 hidden_realops 基于 real_storefront 写入）
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { episodic, fact } from '../brain/hidden_brain.mjs';
import { getRFM, getTouchPlan } from './rfm.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const CRM = path.join(H, 'crm_auto.jsonl');
const ORD = path.join(H, 'orders_auto.jsonl');

function load(p) { if (!fs.existsSync(p)) return []; return fs.readFileSync(p, 'utf8').trim().split('\n').map(l => { try { return JSON.parse(l) } catch (e) { return null } }).filter(Boolean); }
function append(p, o) { fs.appendFileSync(p, JSON.stringify(o) + '\n'); }
function save(p, arr) { fs.writeFileSync(p, arr.map(x => JSON.stringify(x)).join('\n') + (arr.length ? '\n' : '')); }
function now() { return new Date().toISOString(); }

const BASE_DELAY_MS = {
  contacted: 30 * 60 * 1000,
  interested: 45 * 60 * 1000,
  quoted: 60 * 60 * 1000,
  negotiating: 90 * 60 * 1000
};

function delayForStage(stage, tier) {
  const base = BASE_DELAY_MS[stage] || 60 * 60 * 1000;
  const scale = { '核心金牌': 0.5, '潜力银牌': 0.7, '铜牌': 1.0, '培育': 1.5, '流失': 2.0 }[tier] || 1.0;
  return Math.round(base * scale);
}

function canAdvance(c, stage, tier, ts) {
  const last = c.timeline?.findLast?.(e => e.act?.startsWith('auto_'))?.ts || c.updated_at || c.created_at;
  return Date.now() - new Date(last).getTime() >= delayForStage(stage, tier);
}

async function main() {
  const { getRFM } = await import('./rfm.mjs');
  const crm = load(CRM);
  const ts = now();
  let mv = 0;

  for (const c of crm) {
    const rfm = await getRFM(c.lead_id || c.url);
    const tier = rfm.ok ? (rfm.tier || '流失') : (c.tier || '流失');
    const plan = rfm.ok ? rfm : null;
    const touchPlan = plan ? { frequency: plan.touchFreq, channels: plan.channels, commissionPct: plan.commissionPct } : { frequency: 'monthly', channels: ['email'], commissionPct: 0 };

    if (c.tier !== tier) { c.tier = tier; c.channels = touchPlan.channels; c.commission_pct = touchPlan.commissionPct; c.updated_at = now(); }

    if (c.stage === 'contacted' && canAdvance(c, 'contacted', tier, now())) {
      c.stage = 'interested'; c.timeline.push({ ts: now(), act: 'auto_mark_interested', note: `模拟推进（分段：${tier}）` }); c.updated_at = now(); mv++;
    } else if (c.stage === 'interested' && canAdvance(c, 'interested', tier, now())) {
      c.stage = 'quoted'; c.timeline.push({ ts: now(), act: 'auto_quoted', note: `模拟推进（分段：${tier}）` }); c.updated_at = now(); mv++;
    } else if (c.stage === 'quoted' && canAdvance(c, 'quoted', tier, now())) {
      c.stage = 'negotiating'; c.timeline.push({ ts: now(), act: 'auto_negotiating', note: `模拟推进（分段：${tier}）` }); c.updated_at = now(); mv++;
    } else if (c.stage === 'negotiating' && !c.won_auto && canAdvance(c, 'negotiating', tier, now())) {
      c.stage = 'won'; c.won_auto = true; c.timeline.push({ ts: now(), act: 'auto_won', note: `模拟推进（分段：${tier}，无真实支付，不生成订单）` }); c.updated_at = now(); mv++;
    }
  }
  save(CRM, crm);
  episodic('hidden_crm_auto', { moved: mv, orders: 0, note: 'no auto order creation; tier-aware delays' });
  console.log(`[hidden_crm] mv=${mv} ord=0 (auto order creation disabled; tier-aware)`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) { main(); }