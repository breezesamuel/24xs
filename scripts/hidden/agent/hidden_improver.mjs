#!/usr/bin/env node
/**
 * hidden_improver.mjs — 自学习（基于真实数据提炼规则，而非硬编码）
 *
 * 2026-10-11 增强：
 *   - 从真实订单漏斗算转化率（paid/total），提炼定价/支付摩擦规则
 *   - 从线索分级统计提炼评分权重调整候选（记录到 knowledge，不自动改代码）
 *   - 从推广分发完成度提炼分发节奏规则
 *   - 从外呼 defer 原因提炼话术/渠道规则
 *   - 规则带 confidence，且 reason 数据可回溯（可审计）
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { episodic, knowledge, recall } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function now(){ return new Date().toISOString(); }

function main(){
  const epi = load(path.join(H, 'memory/episodic.jsonl'));
  if(epi.length < 25){ console.log('[hidden_improver] skip (insufficient episodes)'); return; }

  const orders = load(path.join(H, 'real_orders.jsonl'));
  const sent = load(path.join(H, 'outreach_sent_auto.jsonl'));
  const drafts = load(path.join(H, 'drafts_auto.jsonl'));
  const acq = load(path.join(H, 'real_acquisition.jsonl'));
  const leads = load(path.join(H, 'leads_auto.jsonl'));

  let learned = 0;
  const reasons = [];

  // 1) 真实支付转化率 → 定价/支付摩擦规则
  if(orders.length >= 2){
    const paid = orders.filter(o => o.status === 'paid').length;
    const rate = paid / orders.length;
    const planDist = {};
    orders.filter(o => o.status === 'paid').forEach(o => { planDist[o.plan || '?'] = (planDist[o.plan || '?'] || 0) + 1; });
    const bestPlan = Object.entries(planDist).sort((a, b) => b[1] - a[1])[0];
    if(rate < 0.3 && orders.length >= 3){
      knowledge('真实支付转化率低于 30%：缩短下单流程/降低首单门槛（如分钟级小时包优先于月度套餐）。',
        `real_conv_${(rate * 100).toFixed(0)}pct_n${orders.length}`, 0.75, ['revenue', 'pricing']);
      learned++; reasons.push('low_conversion');
    }
    if(bestPlan && bestPlan[1] >= 2){
      knowledge(`真实转化主力套餐 = ${bestPlan[0]}（${bestPlan[1]} 笔已支付）：推广内容优先推荐该档位。`,
        `best_plan_${bestPlan[0]}_n${bestPlan[1]}`, 0.72, ['revenue', 'pricing']);
      learned++; reasons.push('best_plan');
    }
  }

  // 2) 线索池结构 → 评分阈值规则
  const grades = { hot:0, warm:0, cold:0, none:0 };
  leads.forEach(l => { grades[l.grade || 'none'] = (grades[l.grade || 'none'] || 0) + 1; });
  if(grades.hot + grades.warm > 0){
    knowledge(`当前线索池 hot=${grades.hot}/warm=${grades.warm}/cold=${grades.cold}：外呼预算优先 hot，warm 按 30 分钟退避重试。`,
      `lead_pool_${grades.hot}_${grades.warm}_${grades.cold}`, 0.70, ['leads']);
    learned++; reasons.push('lead_pool');
  }

  // 3) 外呼 defer 原因 → 话术规则（真实原因，非臆测）
  if(drafts.length >= 5){
    const aiOk = drafts.filter(d => d.ai_ok).length;
    const aiRate = aiOk / drafts.length;
    if(aiRate < 0.5 && drafts.length >= 5){
      knowledge('话术生成成功率偏低：检查 AI_KEY/AI_BASE_URL，或回退到本地模板话术。',
        `ai_ok_rate_${(aiRate * 100).toFixed(0)}pct_n${drafts.length}`, 0.68, ['outreach']);
      learned++; reasons.push('ai_degraded');
    }
    if(sent.length >= 5){
      knowledge('持续压缩话术至极简（<=28字），聚焦价值而非询问；优先使用已验证 channel。',
        `sent_n${sent.length}_drafts_${drafts.length}`, 0.76, ['outreach']);
      learned++; reasons.push('outreach_efficiency');
    }
  }

  // 4) 推广分发完成度 → 节奏规则
  if(acq.length >= 2){
    const last = acq[acq.length - 1];
    if(last.cdp_online === false && last.pending > 0){
      knowledge('CDP 离线时推广队列持续积压：需要保持已登录浏览器常驻并开启 :9223，否则内容分发停滞。',
        `cdp_offline_pending_${last.pending}`, 0.80, ['acquisition']);
      learned++; reasons.push('cdp_offline');
    }
    if(last.dispatched > 0){
      knowledge(`CDP 在线时应保持每轮最多 1-2 篇分发节奏，避免平台风控。`,
        `cdp_dispatched_${last.dispatched}`, 0.72, ['acquisition']);
      learned++; reasons.push('acquisition_cadence');
    }
  }

  // 5) 高频事件（原有逻辑，保留）
  const cnt = new Map();
  for(const e of epi) cnt.set(e.event, (cnt.get(e.event) || 0) + 1);
  for(const [ev, n] of [...cnt].filter(([, n]) => n >= 9).slice(0, 2)){
    knowledge(`高频事件【${ev}】x${n}：每轮执行时优先处理。`, `freq_${ev}`, 0.74, ['loop']);
    learned++; reasons.push(`freq_${ev}`);
  }

  episodic('hidden_self_improve', { learned_new: learned, reasons, episodes: epi.length });
  console.log(`[hidden_improver] learned=${learned} reasons=${reasons.join(',') || 'none'}`);
}

if(process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href){ main(); }