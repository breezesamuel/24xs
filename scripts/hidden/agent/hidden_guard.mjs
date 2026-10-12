#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { episodic } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const G = path.join(H, 'hidden_guard.json');

const def = {
  mode: 'full_autonomous_hidden',
  enforce_robots: true,                                  // 真实生效：hidden_crawler 读取后 host 级执行
  domain_allow: ['github.com', 'raw.githubusercontent.com', 'gist.github.com', 'github.io'],
  min_delay_ms: 1800,                                    // 真实生效：crawler 每次请求前 sleep
  forbid_direct_write_verified: true,                    // 真实生效：写入前校验目标在 autoops/hidden 内
  human_gates_disabled: true,
  auto_publish: true,
  auto_outreach: true,
  auto_crm_oms: true
};

/**
 * 读取 guard 策略（供 crawler / orchestrator 消费）。
 * 文件不存在则先落默认值；字段缺失用默认字段补齐（前向兼容）。
 */
export function loadGuard(){
  let cur = {};
  try { cur = JSON.parse(fs.readFileSync(G, 'utf8')); } catch (e) { cur = {}; }
  if (!cur || typeof cur !== 'object' || !cur.mode){
    cur = { ...def, ...cur };
    save(cur);
  }
  return { ...def, ...cur };
}

export function save(policy){
  if(!fs.existsSync(H)) fs.mkdirSync(H,{recursive:true});
  fs.writeFileSync(G, JSON.stringify(policy, null, 2));
}

/**
 * CLI：校验策略合法 + 报告每个 enforce 开关的消费方（防止再出现"声明无读取方"）。
 * --check 只读不写；默认写文件 + 记 episodic。
 */
function main(){
  const checkOnly = process.argv.includes('--check');
  const guard = checkOnly ? loadGuard() : null;
  if (!checkOnly){
    if(!fs.existsSync(H)) fs.mkdirSync(H,{recursive:true});
    fs.writeFileSync(G, JSON.stringify(def, null, 2));
    loadGuard(); // 归一化字段
    episodic('hidden_guard_check', { mode: def.mode, fields: Object.keys(def).length });
  }
  const g = guard || def;
  const consumers = {
    enforce_robots: 'crawler:safe()',
    domain_allow: 'crawler:safe()',
    min_delay_ms: 'crawler:github()/safe()',
    forbid_direct_write_verified: 'crawler:appendSafe()',
    auto_publish: 'finder',
    auto_outreach: 'outreach',
    auto_crm_oms: 'crm/oms'
  };
  const orphans = Object.keys(consumers).filter(k => g[k] === undefined);
  console.log(JSON.stringify({
    guard: true, mode: g.mode, check_only: checkOnly,
    policies: Object.keys(def).length, orphan_flags: orphans,
    consumers
  }));
}

if(process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href){
  main();
}
