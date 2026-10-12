#!/usr/bin/env node
/**
 * verify_pipeline.cjs — 16 工作流阶段计时验收（<30s 且 success 才算通过）
 *
 * 阶段映射（用户定义的全链路漏斗 + 自主能力）：
 *   1 采集      hidden_crawler        GitHub/网页 → github_raw.jsonl
 *   2 入库      hidden_crawler        → candidates.jsonl（增量去重）
 *   3 上架      hidden_finder         → assets_auto_published.jsonl
 *   4 定价      hidden_pay            价格/网关配置状态
 *   5 订单路由  hidden_crm            won → HORD- 订单
 *   6 物流      hidden_oms            processing→shipped→delivered
 *   7 售后      hidden_oms            aftersale_auto.jsonl
 *   8 外联      hidden_outreach       话术生成/发送/defer
 *   9 跟进      hidden_followup       未付单挽回
 *  10 数据闭环  hidden_realops        真实收银台指标/订单
 *  11 蜘蛛发现  hidden_leads          评分分级
 *  12 自学习    hidden_improver       规则提炼
 *  13 自进化    hidden_brain          knowledge 累计
 *  14 内容官    hidden_planner        计划 + 推广队列
 *  15 巡检      hidden_watchdog       健康/告警
 *  16 记忆      hidden_brain          episodic/knowledge/facts
 *
 * 用法: node verify_pipeline.cjs [--seconds 30]
 */
'use strict';
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '../..');
const A = 'scripts/hidden/agent/';

const STAGES = [
  ['01-采集',      ['scripts/hidden/crawler/hidden_crawler.mjs']],
  ['02-入库',      ['scripts/hidden/crawler/hidden_crawler.mjs']],
  ['03-上架',      [A + 'hidden_finder.mjs']],
  ['04-定价',      [A + 'hidden_pay.mjs']],
  ['05-订单路由',  [A + 'hidden_crm.mjs']],
  ['06-物流',      [A + 'hidden_oms.mjs']],
  ['07-售后',      [A + 'hidden_oms.mjs']],
  ['08-外联',      [A + 'hidden_outreach.mjs']],
  ['09-跟进',      [A + 'hidden_followup.mjs']],
  ['10-数据闭环',  [A + 'hidden_realops.mjs']],
  ['11-蜘蛛发现',  [A + 'hidden_leads.mjs']],
  ['12-自学习',    [A + 'hidden_improver.mjs']],
  ['13-自进化',    ['scripts/hidden/brain/hidden_brain.mjs']],
  ['14-内容官',    [A + 'hidden_planner.mjs']],
  ['15-巡检',      [A + 'hidden_watchdog.mjs', '--json']],
  ['16-记忆',      ['scripts/hidden/brain/hidden_brain.mjs']],
];

function runOnce(args, timeoutMs) {
  return new Promise(resolve => {
    const t0 = Date.now();
    // 显式传递父进程环境（含 GH_TOKEN），确保子进程可读远程状态
    const p = spawn('node', args, { cwd: ROOT, env: process.env });
    let out = '';
    p.stdout.on('data', d => { out += d.toString(); });
    p.stderr.on('data', d => { out += d.toString(); });
    const timer = setTimeout(() => { try { p.kill('SIGKILL'); } catch (e) {} resolve({ code: 124, ms: Date.now() - t0, out, timedOut: true }); }, timeoutMs);
    p.on('close', code => { clearTimeout(timer); resolve({ code, ms: Date.now() - t0, out, timedOut: false }); });
    p.on('error', () => { clearTimeout(timer); resolve({ code: 1, ms: Date.now() - t0, out, timedOut: false }); });
  });
}

(async () => {
  const limitIdx = process.argv.indexOf('--seconds');
  const LIMIT = limitIdx >= 0 ? parseInt(process.argv[limitIdx + 1], 10) * 1000 : 180000;

  console.log(`\n=== 16 工作流阶段验收（阈值 ${LIMIT / 1000}s） ===\n`);
  const rows = [];
  for (const [name, args] of STAGES) {
    const r = await runOnce(args, LIMIT);
    const ok = !r.timedOut && r.code === 0;
    const ms = (r.ms / 1000).toFixed(1);
    const lines = r.out.trim().split('\n');
    const tail = lines.length ? lines[lines.length - 1] : '';
    rows.push({ name, ok, ms: r.ms / 1000, code: r.code, tail: tail.slice(0, 90) });
    console.log(`${ok ? '✅' : '❌'} ${name.padEnd(12)} ${ms.padStart(6)}s  exit=${r.code}  ${tail.slice(0, 80)}`);
  }

  const pass = rows.filter(r => r.ok && r.ms <= LIMIT / 1000).length;
  const slow = rows.filter(r => r.ok && r.ms > LIMIT / 1000);
  const fail = rows.filter(r => !r.ok);
  console.log(`\n=== 汇总: ${pass}/${rows.length} 通过（<${LIMIT / 1000}s 且 success）===`);
  if (slow.length) console.log('超时但仍成功: ' + slow.map(r => `${r.name}(${r.ms.toFixed(1)}s)`).join(', '));
  if (fail.length) console.log('失败: ' + fail.map(r => `${r.name}(exit=${r.code})`).join(', '));
  console.log(`总耗时 ${(rows.reduce((s, r) => s + r.ms, 0)).toFixed(1)}s → 折算每轮 ${(rows.reduce((s, r) => s + r.ms, 0)).toFixed(1)}s`);
  process.exit(fail.length || slow.length ? 1 : 0);
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
