#!/usr/bin/env node
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { episodic } from './brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../');
const H = path.join(ROOT, 'autoops/hidden');
const ST = path.join(H, 'state.json');

function run(rel){
  return new Promise(res=>{
    const p = spawn('node',[path.join(__dirname, rel)],{cwd:ROOT,stdio:'inherit'});
    p.on('close',code=>res({code,rel}));
    p.on('error',()=>res({code:1,rel}));
  });
}
async function main(){
  if(!fs.existsSync(H)) fs.mkdirSync(H,{recursive:true});
  let st={ tick:0, runs:0 }; if(fs.existsSync(ST)){ try{st=JSON.parse(fs.readFileSync(ST,'utf8'));}catch(e){} }
  st.tick=(st.tick||0)+1; st.runs=(st.runs||0)+1; st.mode='full_autonomous_hidden';
  // 心跳 = tick 开始即写。watchdog 在本 tick 中途运行，若只在 tick 末写入，
  // 它读到的永远是上一轮时间戳；GitHub Actions 调度延迟数小时时会被误判 heartbeat_stale。
  // 语义：tick 不启动 = 编排器死亡；tick 中途挂起 = 下次巡检 age 超阈值 → 正确告警。
  st.last_tick=new Date().toISOString();
  try{ fs.writeFileSync(ST, JSON.stringify(st,null,2)); }catch(e){}
  episodic('hidden_orch_start',{tick:st.tick});

  await run('agent/hidden_guard.mjs');
  await run('crawler/hidden_crawler.mjs');
  await run('agent/hidden_finder.mjs');
  await run('agent/hidden_leads.mjs');
  await run('agent/hidden_outreach.mjs');
  await run('agent/hidden_crm.mjs');
  await run('agent/hidden_oms.mjs');
  await run('agent/hidden_pay.mjs');   // 支付网关状态监控 + 待支付处理
  await run('agent/hidden_realops.mjs'); // 真实收银台桥接（订单/营收/健康/获客）
  await run('agent/hidden_followup.mjs'); // 未支付订单挽回（服务端跨设备待付单）
  const watchdog = await run('agent/hidden_watchdog.mjs'); // 运维巡检（无静默失败，异常即告警）
  await run('agent/hidden_planner.mjs');

  // watchdog 检出关键故障 → 透传非零退出码（GitHub Actions 自动发免费告警邮件）
  if(watchdog.code !== 0){
    process.exitCode = watchdog.code;
    console.log(`[hidden_orch] watchdog reported CRITICAL (code=${watchdog.code}) -> exit code propagated`);
  }

  if(st.tick % 6 === 0){
    await run('agent/hidden_improver.mjs');
    episodic('hidden_improve_cycle',{tick:st.tick});
  }

  st.last_tick = new Date().toISOString();
  fs.writeFileSync(ST, JSON.stringify(st,null,2));
  episodic('hidden_orch_end',{tick:st.tick});
  console.log(`[hidden_orch] tick=${st.tick}`);
}
main();
