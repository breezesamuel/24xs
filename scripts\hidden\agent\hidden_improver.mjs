#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { episodic, knowledge, recall } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const SENT = path.join(H, 'outreach_sent_auto.jsonl');

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }

function main(){
  const epi = recall('episodic',80);
  if(epi.length<25){ console.log('[hidden_improver] skip'); return; }
  const sent=load(SENT);
  if(sent.length>=5){
    knowledge('鎸佺画鍘嬬缉璇濇湳鑷虫瀬绠€锛?=28瀛楋級锛岃仛鐒︿环鍊艰€岄潪璇㈤棶銆?,'outreach_freq>=5',0.78,['outreach']);
  }
  const cnt=new Map();
  for(const e of epi){ cnt.set(e.event,(cnt.get(e.event)||0)+1); }
  for(const [ev,n] of [...cnt].filter(([,n])=>n>=9).slice(0,2)){
    knowledge(`楂橀浜嬩欢銆?{ev}銆憍${n}锛氭瘡杞墽琛屾椂浼樺厛澶勭悊銆俙,`freq_${ev}`,0.74,['loop']);
  }
  episodic('hidden_self_improve',{episodes:epi.length,sent:sent.length});
  console.log('[hidden_improver] done');
}
main();
