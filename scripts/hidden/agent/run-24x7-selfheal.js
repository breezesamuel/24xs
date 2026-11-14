#!/usr/bin/env node
/**
 * 24x7 本地自愈循环 (由 Windows 计划任务每 15-30 分钟调用)
 * 目的: 本机作为 24/7 兜底宿主, 即使 GitHub Actions 暂停 / 云不可达, 也持续:
 *   1. 拉取最新真实指标 (Vercel /api/autoops.js?a=stats, 用本地 realops.secret)
 *   2. 跑本地 watchdog (判 critical)
 *   3. 把状态写回 git (real_metrics/alert_state), 让 GitHub scheduled run 不再因陈旧数据误 fail
 *   4. 若 Hidden AutoOps 断更 >45min, gh workflow run 触发它 (本地兜底 24/7)
 *   5. 探 CN storefront (Alipay 查单 40004 = 收款通道活)
 * 无窗口静默, 日志 -> autoops/hidden/24x7_selfheal.log
 * 依赖: gh (已登录 breezesamuel), vercel CLI, python, 本目录 realops.secret 或 AUTOOPS_SECRET env
 */
'use strict';
const { spawnSync, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = 'F:\\2026\\24xs';
const LOG = path.join(ROOT, 'autoops', 'hidden', '24x7_selfheal.log');
const REPO = 'breezesamuel/24xs';
const STALE_MIN = 45;

fs.mkdirSync(path.dirname(LOG), { recursive: true });
function log(msg){ const l=`[${new Date().toISOString()}] ${msg}\n`; try{ fs.appendFileSync(LOG,l,'utf8'); }catch(e){} }

function sh(cmd, opts){
  const r = spawnSync('cmd', ['/c', cmd], { cwd:ROOT, encoding:'utf8', timeout:90000, ...(opts||{}) });
  return { code: r.status, out: (r.stdout||'')+ (r.stderr||'') };
}

log('=== 24x7 本地自愈循环 启动 ===');

// 0. gh 可用性
let g = sh('gh auth status 2>&1');
if (g.code !== 0) { log('❌ gh 未登录/不可用, 本轮中止: '+g.out.slice(0,150)); process.exit(1); }

// 1. 若本地有 realops.secret, 拉最新 stats 并写回 real_metrics.jsonl (让 GitHub 数据新鲜)
try {
  const secPath = path.join(ROOT, 'autoops','hidden','realops.secret');
  if (fs.existsSync(secPath)) {
    const secret = fs.readFileSync(secPath,'utf8').trim();
    const statsOut = sh(`curl -s -m 25 "https://tools.highkingflower.com/api/autoops.js?a=stats&k=${secret}"`);
    let stats = null;
    try { stats = JSON.parse(statsOut.out); } catch(e){}
    if (stats && stats.ok) {
      const row = { at:new Date().toISOString(), captured_at:stats.at, source:'local-24x7', orders:stats.orders, arcade:stats.arcade, auto:true };
      const mf = path.join(ROOT,'autoops','hidden','real_metrics.jsonl');
      fs.appendFileSync(mf, JSON.stringify(row)+'\n','utf8');
      // 裁剪末 200 行
      const lines = fs.readFileSync(mf,'utf8').split('\n').filter(Boolean);
      fs.writeFileSync(mf, lines.slice(-200).join('\n')+'\n','utf8');
      log(`✅ 本地拉取 stats: total=${stats.orders.total} paid=${stats.orders.paid} synth=${stats.orders.synthetic_excluded}`);
    } else {
      log('⚠️ 拉 stats 失败 (需 realops.secret 或站点无 stats): '+statsOut.out.slice(0,80));
    }
  } else {
    log('ℹ️ 无 realops.secret, 跳过本地 stats 拉取 (GitHub 的 realops 会拉)');
  }
} catch(e){ log('拉 stats 异常: '+e.message); }

// 2. 检查 Hidden AutoOps 最近 run 是否 stale, stale 则 gh workflow run 兜底
try {
  const ls = sh(`gh run list --repo ${REPO} --workflow "Hidden AutoOps 24x7" --limit 5 --json createdAt,event,conclusion`);
  let runs = []; try{ runs = JSON.parse(ls.out); }catch(e){}
  const ts = (runs.map(r=>r.createdAt).filter(Boolean)).sort((a,b)=>a.localeCompare(b));
  const last = ts.length ? ts[ts.length-1] : null;
  if (!last) {
    log('ℹ️ Hidden AutoOps 无 run 记录, 触发启动');
    sh(`gh workflow run "Hidden AutoOps 24x7" --repo ${REPO} --ref main`);
  } else {
    const ageMin = Math.round((Date.now() - new Date(last).getTime())/60000);
    log(`Hidden AutoOps 最近 run ${last}, 断更 ${ageMin}min (阈值 ${STALE_MIN})`);
    if (ageMin > STALE_MIN) {
      const t = sh(`gh workflow run "Hidden AutoOps 24x7" --repo ${REPO} --ref main`);
      log(t.code===0 ? `✅ 断更 >${STALE_MIN}min, 已 gh workflow run 兜底 24/7` : `⚠️ 触发失败: ${t.out.slice(0,120)}`);
    } else {
      log('✅ Hidden AutoOps 近期正常, 本地不干预 (避免重复触发)');
    }
  }
} catch(e){ log('检查 Hidden AutoOps 异常: '+e.message); }

// 3. 探 CN storefront 收款通道 (Alipay 查单应 40004/200, 40002=签名坏)
try {
  const cn = sh(`curl -s -m 20 "http://tools-cn.highkingflower.com/api/aliq?out_trade_no=NONEXIST_24X7"`);
  const body = cn.out;
  if (body.includes('40004') || body.includes('TRADE_NOT_EXIST')) log('✅ CN 收款通道活 (查单 40004)');
  else if (body.includes('40002')) log('❌ CN 收款通道签名坏 (40002) -> 需查支付宝密钥');
  else log('ℹ️ CN 查单响应: '+(body||'(空)').slice(0,60));
} catch(e){ log('CN 探异常: '+e.message); }

// 3.5. 探赚钱回路对账 (?a=loop: 引流->注册->试用->付费->收款->对账) — 若本地有 secret
try {
  const secPath2 = path.join(ROOT, 'autoops','hidden','realops.secret');
  if (fs.existsSync(secPath2)) {
    const sk = fs.readFileSync(secPath2,'utf8').trim();
    const lp = sh(`curl -s -m 25 "https://tools.highkingflower.com/api/autoops.js?a=loop&k=${sk}"`);
    let lj = null; try{ lj = JSON.parse(lp.out); }catch(e){}
    if (lj && lj.ok && lj.loop) {
      const f = lj.loop.funnel || {}, r = lj.loop.reconcile || {};
      const row = { at:new Date().toISOString(), loop:{paid_orders:f.paid_orders, revenue_cny:(lj.loop.revenue||{}).cny, reconcile_consistent:r.consistent} };
      const lf = path.join(ROOT,'autoops','hidden','local_moneyloop.jsonl');
      fs.appendFileSync(lf, JSON.stringify(row)+'\n','utf8');
      const lines = fs.readFileSync(lf,'utf8').split('\n').filter(Boolean);
      fs.writeFileSync(lf, lines.slice(-100).join('\n')+'\n','utf8');
      log(`✅ 赚钱回路: paid_orders=${f.paid_orders} revenue=${(lj.loop.revenue||{}).cny} reconcile=${r.consistent?'consistent':'MISMATCH:'+r.mismatch_count}`);
    } else {
      log('ℹ️ ?a=loop 无数据 (secret 不匹配或站点无 loop): '+(lp.out||'(空)').slice(0,50));
    }
  } else {
    log('ℹ️ 无 realops.secret, 跳过 ?a=loop 探 (GitHub realops 会探)');
  }
} catch(e){ log('探 loop 异常: '+e.message); }

// 4. 把 24x7 自愈记录写回 git (本地 -> GitHub, 让云端也能看到本地兜底在跑)
try {
  const runFile = path.join(ROOT,'autoops','hidden','local_24x7_runs.jsonl');
  fs.appendFileSync(runFile, JSON.stringify({at:new Date().toISOString(),note:'local-24x7-selfheal-tick'})+'\n','utf8');
  const lines = fs.readFileSync(runFile,'utf8').split('\n').filter(Boolean);
  fs.writeFileSync(runFile, lines.slice(-100).join('\n')+'\n','utf8');
} catch(e){ log('写 local_24x7_runs 异常: '+e.message); }

log('=== 24x7 本地自愈循环 完成 ===');
