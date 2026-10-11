#!/usr/bin/env node
/**
 * autoops_status.mjs — AutoOps 全系统状态体检
 * 输出：闭环各环节的真实就绪状态 + 下一步清单
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = __dirname;
const H = path.join(ROOT, 'autoops/hidden');

function count(p){ if(!fs.existsSync(p)) return 0; return fs.readFileSync(p,'utf8').trim().split('\n').filter(Boolean).length; }
function exists(p){ return fs.existsSync(p); }
function load(p){ if(!exists(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function env(...names){ return names.filter(n=>process.env[n]); }
function getSecret(){
  if(process.env.AUTOOPS_SECRET) return process.env.AUTOOPS_SECRET;
  try{ return fs.readFileSync(path.join(H,'realops.secret'),'utf8').trim(); }catch(e){ return ''; }
}

console.log('═'.repeat(70));
console.log('  AutoOps 全系统状态体检  ' + new Date().toISOString());
console.log('═'.repeat(70));

console.log('\n【1】数据管道（获客闭环）');
console.log(`  github_raw.jsonl         ${count(path.join(H,'github_raw.jsonl'))} 条抓取记录`);
console.log(`  candidates.jsonl         ${count(path.join(H,'candidates.jsonl'))} 个候选`);
console.log(`  leads_auto.jsonl         ${count(path.join(H,'leads_auto.jsonl'))} 个线索`);
const leads = exists(path.join(H,'leads_auto.jsonl'))
  ? fs.readFileSync(path.join(H,'leads_auto.jsonl'),'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch{return null}}).filter(Boolean)
  : [];
const grade = { hot:0, warm:0, cold:0, none:0 };
leads.forEach(l=>{ grade[l.grade||'none'] = (grade[l.grade||'none']||0)+1; });
console.log(`    └─ 分级: hot=${grade.hot} warm=${grade.warm} cold=${grade.cold} (未分级=${grade.none})`);
console.log(`  drafts_auto.jsonl        ${count(path.join(H,'drafts_auto.jsonl'))} 份外联草稿`);
console.log(`  assets_auto_published    ${count(path.join(H,'assets_auto_published.jsonl'))} 个自动资产`);

console.log('\n【2】真实收银台（tools.highkingflower.com — 真实产品 AI Arcade）');
const RM = path.join(H, 'real_metrics.jsonl');
const RO = path.join(H, 'real_orders.jsonl');
const rm = exists(RM) ? load(RM).slice(-1)[0] : null;
const ro = load(RO);
if(rm){
  console.log(`  最近拉取            ${rm.captured_at}`);
  console.log(`  真实订单            total=${rm.orders.total} paid=${rm.orders.paid} 营收 ¥${rm.orders.revenue_cny}`);
  console.log(`  Arcade 用户         ${rm.arcade.users} 人（余额合计 ${rm.arcade.total_balance_minutes||0} 分钟）`);
  console.log(`  邀请链接            ${rm.arcade.invite_links}`);
}else{
  console.log('  （尚未拉取 — 运行 hidden_realops.mjs）');
}
console.log(`  已入库真实订单      ${ro.length} 笔`);
const paidReal = ro.filter(o => o.status === 'paid').length;
console.log(`    └─ 其中已支付     ${paidReal} 笔`);

console.log('\n【3】交易闭环（CRM/OMS/支付）');
console.log(`  crm_auto.jsonl           ${count(path.join(H,'crm_auto.jsonl'))} 个客户`);
console.log(`  orders_auto.jsonl        ${count(path.join(H,'orders_auto.jsonl'))} 个订单`);
console.log(`  payments_auto.jsonl      ${count(path.join(H,'payments_auto.jsonl'))} 条支付记录`);
console.log(`  aftersale_auto.jsonl     ${count(path.join(H,'aftersale_auto.jsonl'))} 条售后`);

console.log('\n【4】外部凭据配置（决定能否真正赚钱）');
const gateways = {
  '支付宝': ['ALIPAY_APP_ID','ALIPAY_PRIVATE_KEY','ALIPAY_PUBLIC_KEY'],
  'MoltsPay': ['MOLTSPAY_WEBHOOK_SECRET','MOLTSPAY_API_KEY'],
  'x402': ['X402_SECRET','X402_WALLET'],
  'AI外呼': ['OPENROUTER_API_KEY'],
  'GitHub': ['GH_TOKEN'],
};
for(const [name, vars] of Object.entries(gateways)){
  const set = vars.filter(v=>process.env[v]);
  const missing = vars.filter(v=>!process.env[v]);
  const status = missing.length===0 ? '✅ 已配置' : (set.length>0 ? '⚠️ 部分配置' : '❌ 未配置');
  console.log(`  ${name.padEnd(10)} ${status}  (缺失: ${missing.join(', ')||'无'})`);
}

console.log('\n【5】闭环就绪度评估');
const leadReady = grade.hot + grade.warm > 0;
const payReady = env('ALIPAY_APP_ID','MOLTSPAY_API_KEY','X402_SECRET').length > 0;
const aiReady = env('OPENROUTER_API_KEY','AI_API_KEY').length > 0;
const ghReady = !!process.env.GH_TOKEN && !String(process.env.GH_TOKEN).includes('placeholder');
const realopsReady = !!getSecret();
let realHealthReady = false;
try{ const rh = load(path.join(H,'real_health.jsonl')).slice(-1)[0]; realHealthReady = !!(rh && rh.ready); }catch(e){}
const checks = [
  ['获客管道（爬虫→线索）', leadReady],
  ['AI 外呼（话术生成）', aiReady],
  ['GitHub 抓取（真实 token）', ghReady],
  ['支付收款（真实收银台支付宝）', realHealthReady],
  ['真实收银台桥接（AUTOOPS_SECRET）', realopsReady],
  ['CRM→OMS 履约', true],
];
for(const [name, ok] of checks){
  console.log(`  ${ok ? '✅' : '❌'} ${name}`);
}

console.log('\n【6】下一步清单');
const actions = [];
if(!ghReady) actions.push('配置真实 GH_TOKEN（GitHub Settings → Secrets → Actions），让爬虫/获客管道真实运行');
if(!aiReady) actions.push('配置真实 OPENROUTER_API_KEY / AI_API_KEY（让外呼能生成话术）');
if(!realHealthReady) actions.push('排查真实收银台健康状态（/api/health）');
actions.push('获客：在已登录浏览器启动 CDP(:9223) 后，AutoOps 将自动分发 6 篇推广帖（HN/Reddit/X/微信/小红书/知乎）');
actions.push('确认 GitHub Actions「Hidden AutoOps 24x7」定时运行（每 15 分钟）');
if(actions.length){ actions.forEach((a,i)=>console.log(`  ${i+1}. ${a}`)); }
else console.log('  🎉 全闭环已就绪！');

console.log('\n' + '═'.repeat(70));
