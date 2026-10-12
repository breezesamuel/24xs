#!/usr/bin/env node
/**
 * hidden_followup.mjs — 未支付订单挽回（服务端跨设备待付单）
 *
 * 场景：用户已生成支付单（status=created）但未完成支付。
 * 本地 localStorage 的 pending_ 只在同一设备有效；跨设备/换浏览器即丢失。
 * 本模块把待付单写入服务端 arc_pend_<ref>（24h 有效），
 * 用户任何设备访问 arcade 都会看到"继续支付"提示 → 挽回营收。
 *
 * 规则：
 *   - 只写服务端待付单 KV（arc_pend_<ref>），绝不触碰计费锚点
 *   - 已支付订单自动清除对应 ref 的待付单
 *   - 超过 24h 的未付单视为放弃，仍写一次（让用户最后一次看到后过期）
 *   - 需要 AUTOOPS_SECRET（fail-closed：无密钥则记录 deferred）
 *
 * 2026-10-12（方案B：AI Planner 执行闭环）：
 *   - basicFollowupScan()      原有服务端待付单挽回逻辑（保留，作为回退基线）
 *   - executePlannedFollowup() 链式执行：扫描未付单 → planner 生成计划 → executePlan 执行 → 记录结果
 *   - main()                   先跑基础挽回，再跑 planner 链式执行（可用 --no-plan 跳过）
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { episodic } from '../brain/hidden_brain.mjs';
import { buildPlan, executePlan } from './hidden_planner.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const REALORD = path.join(H, 'real_orders.jsonl');
const SECRET_FILE = path.join(H, 'realops.secret');
const STOREFRONT = process.env.STOREFRONT_BASE || 'https://tools.highkingflower.com';

const PENDING_TTL_MS = 24 * 60 * 60 * 1000;

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function now(){ return new Date().toISOString(); }

function getSecret(){
  if(process.env.AUTOOPS_SECRET) return process.env.AUTOOPS_SECRET;
  try{ return fs.readFileSync(SECRET_FILE,'utf8').trim(); }catch(e){ return ''; }
}

// 从 out_trade_no 解析 ref：BDS_<ref>_<plan>_<ts>
// ref 可能为空（如 BDS__m10_xxx）→ 回退到稳定派生 ref，保证待付单有归属
function refOf(outTradeNo){
  const parts = String(outTradeNo || '').split('_');
  let ref = '';
  if(parts.length >= 4 && parts[0] === 'BDS'){
    ref = parts.slice(1, -2).join('_') || '';
  }
  if(!ref) ref = parts[1] || '';
  if(!ref){
    // 稳定派生：'P' + base36(时间戳末6位) + 末2位plan标识，保证同单同 ref
    const m = String(outTradeNo || '').match(/(\d{10,})$/);
    const ts = m ? m[1] : String(Date.now());
    ref = 'P' + ts.slice(-6);
  }
  return ref;
}

async function callApi(params){
  const secret = getSecret();
  if(!secret) return { ok:false, reason:'no_secret' };
  const url = `${STOREFRONT}/api/pending?k=${encodeURIComponent(secret)}&` + new URLSearchParams(params).toString();
  try{
    const res = await fetch(url, { signal: AbortSignal.timeout(15000) });
    const j = await res.json().catch(() => ({}));
    return { ok: res.ok && (j.ok !== false), status: res.status, body: j };
  }catch(e){
    return { ok:false, reason: String(e && e.message || e).slice(0, 120) };
  }
}

// ===== 基础挽回（原有逻辑，保留为回退基线）=====
async function basicFollowupScan(){
  if(!fs.existsSync(H)) fs.mkdirSync(H, { recursive:true });
  const secret = getSecret();
  if(!secret){
    append(path.join(H, 'followup.jsonl'), { at: now(), deferred:true, reason:'no_secret', auto:true });
    console.log('[hidden_followup] deferred: no AUTOOPS_SECRET');
    return { deferred:true, reason:'no_secret' };
  }

  const orders = load(REALORD);
  const unpaid = orders.filter(o => o.status !== 'paid');
  const paidRefs = new Set(orders.filter(o => o.status === 'paid').map(o => refOf(o.out_trade_no)));

  let restored = 0, cleared = 0, skipped = 0;
  const details = [];
  for(const o of unpaid){
    const ref = refOf(o.out_trade_no);
    if(!ref){ skipped++; continue; }
    if(paidRefs.has(ref)){ skipped++; continue; }
    const age = Date.now() - (o.first_seen_at ? new Date(o.first_seen_at).getTime() : Date.now());
    // 超过 TTL 的未付单：不再推（用户已流失），只记录
    if(age > PENDING_TTL_MS){ skipped++; continue; }

    const r = await callApi({ op:'set', ref, plan:o.plan || '', amount:o.amount || '', out_trade_no:o.out_trade_no });
    if(r.ok){ restored++; details.push({ out_trade_no:o.out_trade_no, ref, result:'written' }); }
    else details.push({ out_trade_no:o.out_trade_no, ref, result:'failed:' + (r.body && r.body.error || r.reason || r.status) });
  }

  // 已支付的 ref：清除待付单（避免打扰已付费用户）
  for(const ref of paidRefs){
    const r = await callApi({ op:'clear', ref });
    if(r.ok) cleared++;
  }

  const rec = { at: now(), unpaid_scanned: unpaid.length, restored, cleared, skipped, details, auto:true };
  append(path.join(H, 'followup.jsonl'), rec);
  episodic('hidden_followup', { restored, cleared, skipped, unpaid: unpaid.length });
  console.log(`[hidden_followup] scanned=${unpaid.length} restored=${restored} cleared=${cleared} skipped=${skipped}`);
  return { unpaid: unpaid.length, restored, cleared, skipped };
}

// ===== 方案B：planner 计划链式执行 =====
// 扫描未付单 → planner 生成计划 → executePlan(仅 followup 类型) 执行 → 记录结果
async function executePlannedFollowup(){
  const orders = load(REALORD);
  const unpaid = orders.filter(o => o.status !== 'paid');

  // 1) planner 基于真实状态生成计划
  const plan = buildPlan();

  // 2) 执行 followup 类动作（话术准备 + 记录；实际投递走服务端待付单渠道）
  const summary = await executePlan(plan, { kinds: ['followup'] });

  // 3) 记录链式执行结果
  const result = {
    at: now(),
    chain: 'executePlannedFollowup',
    focus: plan.focus,
    unpaid_scanned: unpaid.length,
    executed: summary.results,
    auto: true
  };
  append(path.join(H, 'followup.jsonl'), result);
  console.log(`[hidden_followup] planned chain: focus=${plan.focus} unpaid=${unpaid.length} kinds=${summary.results.length}`);
  return result;
}

async function main(){
  // 1) 基础服务端待付单挽回（回退基线，始终执行）
  await basicFollowupScan();

  // 2) 方案B：planner 计划链式执行（可用 --no-plan 跳过）
  if(process.argv.includes('--no-plan')) return { planned:false };
  try{
    await executePlannedFollowup();
    return { planned:true };
  }catch(e){
    console.log(`[hidden_followup] plan chain failed, base scan retained: ${e.message}`);
    episodic('hidden_followup_plan_error', { error: String(e && e.message || e) });
    return { planned:false, error: String(e && e.message || e) };
  }
}

// 仅在被直接运行时执行（被 import 时不产生副作用）
if(process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href){
  main().catch(e => {
    console.log(`[hidden_followup] error: ${e.message}`);
    episodic('hidden_followup_error', { error: String(e && e.message || e) });
  });
}
