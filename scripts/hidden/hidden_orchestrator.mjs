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
  episodic('hidden_orch_start',{tick:st.tick});

  await run('agent/hidden_guard.mjs');
  await run('crawler/hidden_crawler.mjs');
  await run('agent/hidden_finder.mjs');
  await run('agent/hidden_leads.mjs');
  await run('agent/hidden_outreach.mjs');
  await run('agent/hidden_crm.mjs');
  await run('agent/hidden_oms.mjs');
  await run('agent/hidden_planner.mjs');

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
