#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const MEM = path.join(ROOT, 'autoops/hidden/memory');
const EP = path.join(MEM, 'episodic.jsonl');
const KN = path.join(MEM, 'knowledge.jsonl');
const FA = path.join(MEM, 'facts.jsonl');
const PR = path.join(MEM, 'profiles.jsonl');
const CV = path.join(MEM, 'conversations.jsonl');
const TG = path.join(MEM, 'targets.jsonl');

function ensure(){
  if(!fs.existsSync(MEM)) fs.mkdirSync(MEM,{recursive:true});
  [EP,KN,FA,PR,CV,TG].forEach(p=>{ if(!fs.existsSync(p)) fs.writeFileSync(p,''); });
}

function h(s){ return crypto.createHash('sha256').update(String(s)).digest('hex').slice(0,16); }
function now(){ return new Date().toISOString(); }
function uid(prefix=''){ return `${prefix}${Date.now()}-${Math.random().toString(36).slice(2,10)}`; }
function append(p,obj){ fs.appendFileSync(p, JSON.stringify(obj)+'\n'); }
function load(p,limit=20){
  if(!fs.existsSync(p)||!fs.statSync(p).size) return [];
  const lines = fs.readFileSync(p,'utf8').trim().split('\n');
  const arr = lines.map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean);
  return arr.slice(-limit); // newest last (chronological)
}

export function episodic(event, details={}){
  ensure(); const rec={ id:uid('epi-'), ts:now(), event, details, agent:'hidden_autoops', mode:'full_autonomous' };
  append(EP,rec); return rec;
}
export function knowledge(rule, reason='', confidence=0.72, tags=[]){
  ensure(); const rec={ id:uid('kn-'), ts:now(), rule, reason, confidence, tags, hits:0, last_used:null, weight:1.0, auto_applied:true };
  append(KN,rec); return rec;
}
export function fact(key, value={}, source='hidden', confirmed=true){
  ensure(); const rec={ id:uid('fact-'), ts:now(), key, value, source, confirmed };
  append(FA,rec); return rec;
}
export function profile(url, meta={}){
  ensure(); const rec={ id:uid('prf-'), ts:now(), url, meta, stage:'discovered', trust:0.55, auto_tracked:true };
  append(PR,rec); return rec;
}
export function conversation(lead_id, role='auto', content=''){
  ensure(); const rec={ id:uid('cv-'), ts:now(), lead_id, role, content, auto:true };
  append(CV,rec); return rec;
}
export function target(meta={}){
  ensure(); const rec={ id:uid('tgt-'), ts:now(), ...meta, active:true, auto_added:true };
  append(TG,rec); return rec;
}
export function recall(kind='knowledge', limit=20){
  ensure();
  if(kind==='episodic') return load(EP,limit);
  if(kind==='facts') return load(FA,limit);
  if(kind==='profiles') return load(PR,limit);
  if(kind==='conversations') return load(CV,limit);
  if(kind==='targets') return load(TG,limit);
  return load(KN,limit);
}
export function all(limit=12){
  ensure();
  return { episodic:load(EP,limit), knowledge:load(KN,limit), facts:load(FA,limit), profiles:load(PR,limit), conversations:load(CV,limit), targets:load(TG,limit) };
}
export default { episodic, knowledge, fact, profile, conversation, target, recall, all };