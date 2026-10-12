#!/usr/bin/env node
/**
 * hidden_planner.mjs — 动态规划器 + 执行器（读取真实状态生成计划并执行）
 *
 * 2026-10-11 增强：不再写死任务列表，而是读取
 *   - 真实收银台指标 real_metrics.jsonl（订单/营收/Arcade 用户）
 *   - 真实订单 real_orders.jsonl（未支付/已支付漏斗）
 *   - 线索分级统计 leads_auto.jsonl（hot/warm/cold）
 *   - 推广分发队列 schedule.json（待发帖数）
 * 按优先级输出下一步该干什么，并推入 hidden_tasks.jsonl 任务队列。
 *
 * 2026-10-12 增强（方案B：AI Planner 执行闭环）：
 *   - buildPlan()            生成结构化计划（tasks + snapshot）
 *   - executePlan()          按任务类型分派执行（followup/outbound/content/payments）
 *   - executeFollowupPlan()  未支付订单跟进（生成话术 + 记录动作，不做破坏性投递）
 *   - executeOutboundCall()  hot 线索外呼话术准备
 *   - executeContentPlan()   推广内容分发（CDP 离线则 fail-closed 顺延）
 *   - executePaymentsPlan()  收款链路检查
 *   - generateTalkingPoints() AI 生成话术（无 key 时模板回退）
 *   - recordRule()           执行记录持久化（planner_actions.jsonl + episodic）
 *
 * 直接运行时 main() 自动生成计划并执行（followup 由 hidden_followup.mjs 链式执行，避免重复）。
 * 被 import 时不会触发 main() 副作用（见文件末尾 isMain 守卫）。
 */
import fs from 'fs';
import path from 'path';
import net from 'net';
import { fileURLToPath, pathToFileURL } from 'url';
import { spawnSync } from 'child_process';
import { episodic, knowledge, recall } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const PLAN = path.join(H, 'hidden_plan.json');
const TASKS = path.join(H, 'hidden_tasks.jsonl');
const ACTIONS = path.join(H, 'planner_actions.jsonl');
const REALORD = path.join(H, 'real_orders.jsonl');
const LEADS = path.join(H, 'leads_auto.jsonl');
const METRICS = path.join(H, 'real_metrics.jsonl');
const SCHEDULE = 'C:/bingdashan/promotion/schedule.json';
const CDP_PORT = 9223;

// 同一订单/线索的动作冷却窗口，避免 15 分钟循环重复准备同一对象
const ACTION_COOLDOWN_MS = 6 * 60 * 60 * 1000;

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function now(){ return new Date().toISOString(); }
function read(p){ try{ return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p,'utf8')) : null; }catch(e){ return null; } }

function latestMetrics(){
  const rows = load(METRICS);
  return rows.length ? rows[rows.length - 1] : null;
}

function funnel(){
  const orders = load(REALORD);
  const paid = orders.filter(o => o.status === 'paid').length;
  return { total: orders.length, paid, unpaid: orders.length - paid };
}

function leadGrades(){
  const leads = load(LEADS);
  const g = { hot:0, warm:0, cold:0, none:0 };
  leads.forEach(l => { g[l.grade || 'none'] = (g[l.grade || 'none'] || 0) + 1; });
  return g;
}

function pendingPromos(){
  // 存在两份 schedule.json（仓库内 promotion/ 与 C:/bingdashan/promotion/，被不同模块写入）
  // 取并集口径：pending/posts 取最大值，cdp_known 取任一明确值
  const sources = [ path.join(ROOT, 'promotion/schedule.json'), SCHEDULE ];
  let pending = 0, posts = 0, cdp = null;
  for(const p of sources){
    const s = read(p);
    if(!s || !Array.isArray(s.queue)) continue;
    posts = Math.max(posts, s.queue.length);
    pending = Math.max(pending, s.queue.filter(q => !q.posted).length);
    if(s.cdp_known === true) cdp = true;
    else if(s.cdp_known === false && cdp === null) cdp = false;
  }
  return { posts, pending, cdp_known: cdp };
}

// ===== 方案B：执行器 =====

// 轻量探测本地 CDP（:9223）是否在线，避免长时间的失败阻塞
function isCdpOnline(timeoutMs = 800){
  return new Promise(res => {
    const sock = net.connect({ host:'127.0.0.1', port: CDP_PORT });
    let settled = false;
    const done = ok => { if(settled) return; settled = true; try{ sock.destroy(); }catch(e){} res(ok); };
    const t = setTimeout(() => done(false), timeoutMs);
    sock.once('connect', () => { clearTimeout(t); done(true); });
    sock.once('error', () => { clearTimeout(t); done(false); });
  });
}

// 共用 AI 调用（与 hidden_outreach.mjs 保持一致的环境变量约定）
async function ai(prompt, { maxTokens = 200, system } = {}){
  const key = process.env.OPENROUTER_API_KEY || process.env.AI_API_KEY || '';
  const base = process.env.AI_BASE_URL || 'https://openrouter.ai/api/v1/chat/completions';
  const model = process.env.AI_MODEL || 'deepseek/deepseek-chat-v3-0324:free';
  if(!key) return { ok:false, reason:'no_key', retryable:true };
  try{
    const res = await fetch(base, {
      method:'POST',
      headers:{ 'Authorization':`Bearer ${key}`, 'Content-Type':'application/json', 'HTTP-Referer':'https://app.highkingflower.com', 'X-Title':'24XS-Hidden-Planner' },
      body: JSON.stringify({
        model, temperature:0.2, max_tokens:maxTokens,
        messages:[
          { role:'system', content: system || '你是全自动商务执行助理。输出极简、合规、不夸大、不承诺的中文内容。' },
          { role:'user', content: prompt }
        ]
      }),
      signal: AbortSignal.timeout(20000)
    });
    if(!res.ok) return { ok:false, reason:`http_${res.status}`, retryable: res.status === 429 || res.status >= 500 };
    const j = await res.json();
    const txt = (j.choices?.[0]?.message?.content || '').trim();
    if(!txt) return { ok:false, reason:'empty', retryable:true };
    return { ok:true, text: txt };
  }catch(e){ return { ok:false, reason:String(e && e.message || e).slice(0,120), retryable:true }; }
}

// 执行记录持久化（append-only，非破坏性）
export function recordRule(kind, payload = {}){
  const rec = { at: now(), kind, ...payload, auto:true };
  append(ACTIONS, rec);
  episodic('planner_rule', { kind, status: payload.status });
  return rec;
}

// 生成跟进/外呼话术：优先 AI，无 key 或失败则模板回退（fail-closed 但可用）
export async function generateTalkingPoints(kind = 'recovery', ctx = {}){
  const templates = {
    recovery: [
      '您好，看到您有一笔未完成的订单，需要我帮您确认套餐吗？',
      '首单有赠送额度，今天完成支付即可生效，我可以帮您处理。',
      '如果支付遇到问题，我可以提供其他开通方式。'
    ],
    outbound: [
      '您好，看到您关注过我们的在线工具，可提供一次免费体验。',
      '我们支持分钟级计费、按需开通，无需长期承诺。',
      '如需了解套餐差异，我可以发一份简单对比给您。'
    ]
  };
  const tpl = templates[kind] || templates.recovery;
  const key = process.env.OPENROUTER_API_KEY || process.env.AI_API_KEY || '';
  if(!key) return { ai_ok:false, source:'template', points: tpl };

  const subject = ctx.order
    ? `订单套餐 ${ctx.order.plan || ''} 金额 ¥${ctx.order.amount || ''}`
    : (ctx.lead ? `线索 ${ctx.lead.url || ctx.lead.id || ''}` : '通用场景');
  const prompt = `场景：${kind}。对象：${subject}。生成 3 条极简、合规的中文跟进话术，每行一条，每条 <=28 字，不夸大、不承诺。只返回话术。`;
  const r = await ai(prompt, { maxTokens:180 });
  if(!r.ok) return { ai_ok:false, source:'template', reason:r.reason, points: tpl };
  const points = r.text.split('\n')
    .map(s => s.replace(/^[\s\-\d\.、。]+/, '').trim())
    .filter(Boolean)
    .slice(0,3);
  return { ai_ok:true, source:'ai', points: points.length ? points : tpl };
}

// 最近动作索引：kind|keyField|key -> 最近一次动作时间戳
function loadLastActions(){
  const last = new Map();
  for(const r of load(ACTIONS)){
    if(r.summary || !r.kind) continue;
    const t = new Date(r.at).getTime();
    if(!Number.isFinite(t)) continue;
    if(r.order_ref) last.set(`${r.kind}|order_ref|${r.order_ref}`, t);
    if(r.lead_id) last.set(`${r.kind}|lead_id|${r.lead_id}`, t);
  }
  return last;
}
function inCooldown(last, kind, keyField, keyValue, withinMs = ACTION_COOLDOWN_MS){
  const t = last.get(`${kind}|${keyField}|${keyValue}`);
  return !!t && (Date.now() - t) < withinMs;
}

// 未支付订单跟进：为每笔未付单准备话术并记录（实际投递走服务端待付单渠道）
export async function executeFollowupPlan(plan = {}){
  const orders = load(REALORD).filter(o => o.status !== 'paid');
  const last = loadLastActions();
  const pending = orders.filter(o => !inCooldown(last, 'followup', 'order_ref', o.out_trade_no));
  const out = [];
  for(const o of pending.slice(0, 5)){
    const tp = await generateTalkingPoints('recovery', { order:o });
    recordRule('followup', {
      order_ref: o.out_trade_no, plan: o.plan, amount: o.amount,
      talking_points: tp.points, ai_ok: tp.ai_ok, source: tp.source, reason: tp.reason, status: 'prepared'
    });
    out.push({ order_ref: o.out_trade_no, points: tp.points.length, ai_ok: tp.ai_ok });
  }
  return {
    kind:'followup',
    status: pending.length ? 'prepared' : (orders.length ? 'cooldown' : 'noop'),
    count: out.length,
    skipped_cooldown: orders.length - pending.length,
    results: out
  };
}

// hot 线索外呼：生成话术并记录（真实外呼由 hidden_outreach.mjs 投递）
export async function executeOutboundCall(plan = {}){
  const leads = load(LEADS).filter(l => l.grade === 'hot' && !l.contacted);
  if(leads.length === 0){
    recordRule('outbound', { status:'no_hot_leads', hot:0 });
    return { kind:'outbound', status:'no_hot_leads', count:0, results:[] };
  }
  const last = loadLastActions();
  const pending = leads.filter(l => !inCooldown(last, 'outbound', 'lead_id', l.id));
  const out = [];
  for(const l of pending.slice(0, 5)){
    const tp = await generateTalkingPoints('outbound', { lead:l });
    recordRule('outbound', { lead_id:l.id, url:l.url, talking_points: tp.points, ai_ok: tp.ai_ok, source: tp.source, reason: tp.reason, status:'prepared' });
    out.push({ lead_id:l.id, ai_ok: tp.ai_ok });
  }
  return {
    kind:'outbound',
    status: pending.length ? 'prepared' : 'cooldown',
    count: out.length,
    skipped_cooldown: leads.length - pending.length,
    results: out
  };
}

// 推广内容分发：CDP 离线则 fail-closed 顺延；在线默认仅记录 ready，PLANNER_CONTENT_LIVE=1 才真发
export async function executeContentPlan(plan = {}){
  const promos = pendingPromos();
  if(promos.pending <= 0){
    recordRule('content', { status:'noop', pending:0 });
    return { kind:'content', status:'noop', pending:0 };
  }
  const cdp = await isCdpOnline();
  if(!cdp){
    recordRule('content', { status:'deferred_cdp_offline', pending: promos.pending });
    console.log(`[planner-execute] content deferred: CDP :${CDP_PORT} offline, pending=${promos.pending}`);
    return { kind:'content', status:'deferred_cdp_offline', pending: promos.pending };
  }
  if(process.env.PLANNER_CONTENT_LIVE !== '1'){
    recordRule('content', { status:'ready', pending: promos.pending, note:'set PLANNER_CONTENT_LIVE=1 to auto-post' });
    return { kind:'content', status:'ready', pending: promos.pending };
  }
  const script = path.join(__dirname, 'content-distributor.js');
  const r = spawnSync(process.execPath, [script, 'run-schedule', '1'], { cwd: ROOT, encoding:'utf8', timeout: 90000 });
  const stdout = String(r.stdout || '');
  const posted = (stdout.match(/✅/g) || []).length;
  const status = (r.status === 0 && posted > 0) ? 'posted' : 'attempted';
  recordRule('content', { status, pending: promos.pending, exit: r.status, posted, err: String(r.stderr || '').slice(0,160) });
  return { kind:'content', status, pending: promos.pending, posted, exit: r.status };
}

// 收款链路检查（只读统计，不做资金操作）
export async function executePaymentsPlan(plan = {}){
  const f = funnel();
  const m = latestMetrics();
  const revenue = m && m.orders ? m.orders.revenue_cny : 0;
  recordRule('payments', { status:'checked', paid: f.paid, unpaid: f.unpaid, revenue_cny: revenue });
  return { kind:'payments', status:'checked', paid: f.paid, unpaid: f.unpaid, revenue_cny: revenue };
}

// 计划执行分派
export async function executePlan(plan = {}, opts = {}){
  const kinds = Array.isArray(opts.kinds) && opts.kinds.length
    ? opts.kinds
    : ['followup','outbound','content','payments'];
  const has = id => (plan.tasks || []).some(t => t.id === id);
  const f = funnel();
  const leads = leadGrades();
  const results = [];

  if(kinds.includes('followup') && (has('HB1') || f.unpaid > 0)) results.push(await executeFollowupPlan(plan));
  if(kinds.includes('outbound') && (has('HB4') || leads.hot > 0)) results.push(await executeOutboundCall(plan));
  if(kinds.includes('content') && (has('HB2') || has('HB3'))) results.push(await executeContentPlan(plan));
  if(kinds.includes('payments') && (has('HB5') || f.paid > 0)) results.push(await executePaymentsPlan(plan));

  const summary = { at: now(), focus: plan.focus || '', kinds, results };
  append(ACTIONS, { summary:true, ...summary });
  episodic('planner_execute', { focus: summary.focus, kinds: kinds.join(','), executed: results.length });
  console.log(`[planner-execute] kinds=${kinds.join(',')} executed=${results.length}`);
  return summary;
}

// ===== 计划生成（无副作用，供 main 与 hidden_followup 复用）=====
export function buildPlan(){
  const m = latestMetrics();
  const f = funnel();
  const leads = leadGrades();
  const promos = pendingPromos();
  const kn = recall('knowledge', 5).map(k => k.rule).slice(-2);

  // 动态生成任务（按真实瓶颈排序）
  const tasks = [];
  const push = (id, name, pri, why) => tasks.push({ id, name, pri, why, auto: true });

  if(f.total === 0){
    push('HB1', '等待真实首单', 100, '收银台尚无真实订单，优先获客');
  } else {
    push('HB1', `跟进 ${f.unpaid} 笔未支付订单`, 95, `漏斗:${f.total} 单 / ${f.paid} 已付`);
  }

  const zeroUsers = !m || (m.arcade && m.arcade.users === 0);
  if(zeroUsers){
    push('HB2', 'Arcade 零用户 → 分发推广内容', 98, '零用户即零留存，内容分发是当前最高杠杆');
  } else {
    push('HB2', '监控 Arcade 活跃与留存', 80, `用户 ${m.arcade.users}，余额 ${m.arcade.total_balance_minutes || 0} 分钟`);
  }

  if(promos.pending > 0){
    push('HB3', `分发 ${promos.pending} 篇推广（CDP 在线时）`, 92 - promos.pending, '等待 CDP 浏览器在线');
  }

  if(leads.hot > 0){
    push('HB4', `外呼 ${Math.min(leads.hot, 10)} 个 hot 线索`, 88, `hot=${leads.hot} warm=${leads.warm} cold=${leads.cold}`);
  }

  if(f.paid > 0){
    push('HB5', '履约已支付订单（自动）', 85, `已支付 ${f.paid} 笔，走数字交付`);
  }

  push('HB6', 'CRM→OMS 状态机推进', 82, '自动流转');
  push('HB7', '自学习：从真实转化提炼规则', 70, `知识库:${kn.length ? '已有' : '空'}`);

  tasks.sort((a, b) => b.pri - a.pri);

  return {
    ts: now(),
    mode: 'full_autonomous_hidden',
    focus: tasks[0].name,
    tasks,
    snapshot: {
      revenue_cny: m && m.orders ? m.orders.revenue_cny : 0,
      orders: f,
      leads,
      promos,
      arcade_users: m ? m.arcade.users : 0,
      ai_key: !!(process.env.OPENROUTER_API_KEY || process.env.AI_API_KEY)
    }
  };
}

async function printStatus(){
  const plan = buildPlan();
  const cdp = await isCdpOnline(500);
  const lastExec = load(ACTIONS).filter(r => r.summary).slice(-1)[0] || null;
  const status = {
    at: now(),
    ai_key: plan.snapshot.ai_key,
    cdp_online: cdp,
    cdp_port: CDP_PORT,
    pending_promos: plan.snapshot.promos.pending,
    unpaid_orders: plan.snapshot.orders.unpaid,
    paid_orders: plan.snapshot.orders.paid,
    revenue_cny: plan.snapshot.revenue_cny,
    hot_leads: plan.snapshot.leads.hot,
    warm_leads: plan.snapshot.leads.warm,
    focus: plan.focus,
    last_execution: lastExec ? { at: lastExec.at, kinds: lastExec.kinds, results: lastExec.results } : null
  };
  console.log(JSON.stringify(status, null, 2));
  return status;
}

async function main(){
  // --status：只读自检（不写计划、不执行），用于确认 planner 就绪状态
  if(process.argv.includes('--status')){
    await printStatus();
    return;
  }

  const plan = buildPlan();

  fs.writeFileSync(PLAN, JSON.stringify(plan, null, 2));

  // 把 TOP3 任务推入可消费的任务队列（供执行器/看板读取）
  for(const t of plan.tasks.slice(0, 3)){
    append(TASKS, { task_id: t.id, name: t.name, pri: t.pri, why: t.why, ts: now(), auto: true });
  }

  episodic('hidden_planner_dynamic', { focus: plan.focus, tasks: plan.tasks.length, snapshot: plan.snapshot });
  console.log(`[hidden_planner] focus=${plan.focus} (revenue=¥${plan.snapshot.revenue_cny}, promos_pending=${plan.snapshot.promos.pending}, hot=${plan.snapshot.leads.hot}, ai_key=${plan.snapshot.ai_key})`);

  // 执行闭环：followup 由 hidden_followup.mjs 链式执行，这里默认执行其余类型，避免重复
  // --execute-all 可用于一次性执行全部类型（含 followup）；--no-execute 仅生成计划
  if(!process.argv.includes('--no-execute')){
    const kinds = process.argv.includes('--execute-all')
      ? ['followup', 'outbound', 'content', 'payments']
      : ['outbound', 'content', 'payments'];
    await executePlan(plan, { kinds });
  }
}

// 仅在被直接运行时执行 main()（被 import 时不产生副作用）
if(process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href){
  main().catch(e => {
    console.log(`[hidden_planner] error: ${e.message}`);
    episodic('hidden_planner_error', { error: String(e && e.message || e) });
  });
}
