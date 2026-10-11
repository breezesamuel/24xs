#!/usr/bin/env node
/**
 * hidden_planner.mjs — 动态规划器（读取真实状态生成计划）
 *
 * 2026-10-11 增强：不再写死任务列表，而是读取
 *   - 真实收银台指标 real_metrics.jsonl（订单/营收/Arcade 用户）
 *   - 真实订单 real_orders.jsonl（未支付/已支付漏斗）
 *   - 线索分级统计 leads_auto.jsonl（hot/warm/cold）
 *   - 推广分发队列 schedule.json（待发帖数）
 * 按优先级输出下一步该干什么，并推入 hidden_tasks.jsonl 任务队列。
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { episodic, knowledge, recall } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const PLAN = path.join(H, 'hidden_plan.json');
const TASKS = path.join(H, 'hidden_tasks.jsonl');
const SCHEDULE = 'C:/bingdashan/promotion/schedule.json';

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function now(){ return new Date().toISOString(); }
function read(p){ try{ return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p,'utf8')) : null; }catch(e){ return null; } }

function latestMetrics(){
  const rows = load(path.join(H, 'real_metrics.jsonl'));
  return rows.length ? rows[rows.length - 1] : null;
}

function funnel(){
  const orders = load(path.join(H, 'real_orders.jsonl'));
  const paid = orders.filter(o => o.status === 'paid').length;
  return { total: orders.length, paid, unpaid: orders.length - paid };
}

function leadGrades(){
  const leads = load(path.join(H, 'leads_auto.jsonl'));
  const g = { hot:0, warm:0, cold:0, none:0 };
  leads.forEach(l => { g[l.grade || 'none'] = (g[l.grade || 'none'] || 0) + 1; });
  return g;
}

function pendingPromos(){
  const s = read(SCHEDULE);
  if(!s || !Array.isArray(s.queue)) return { posts: 0, pending: 0, cdp_known: null };
  return {
    posts: s.queue.length,
    pending: s.queue.filter(q => !q.posted).length,
    cdp_known: s.cdp_known === true ? true : (s.cdp_known === false ? false : null)
  };
}

function main(){
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

  const plan = {
    ts: now(),
    mode: 'full_autonomous_hidden',
    focus: tasks[0].name,
    tasks,
    snapshot: {
      revenue_cny: m ? m.orders.revenue_cny : 0,
      orders: f,
      leads,
      promos,
      arcade_users: m ? m.arcade.users : 0
    }
  };

  fs.writeFileSync(PLAN, JSON.stringify(plan, null, 2));

  // 把 TOP3 任务推入可消费的任务队列（供执行器/看板读取）
  for(const t of tasks.slice(0, 3)){
    append(TASKS, { task_id: t.id, name: t.name, pri: t.pri, why: t.why, ts: now(), auto: true });
  }

  episodic('hidden_planner_dynamic', { focus: plan.focus, tasks: tasks.length, snapshot: plan.snapshot });
  console.log(`[hidden_planner] focus=${plan.focus} (revenue=¥${plan.snapshot.revenue_cny}, promos_pending=${promos.pending}, hot=${leads.hot})`);
}

main();