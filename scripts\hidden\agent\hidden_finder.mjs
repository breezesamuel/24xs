#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';
import { episodic } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const CAND = path.join(H, 'candidates.jsonl');
const PUB = path.join(H, 'assets_auto_published.jsonl');
const LOG = path.join(H, 'finder_log.jsonl');

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function h(s){ return crypto.createHash('sha256').update(String(s)).digest('hex').slice(0,10); }
function now(){ return new Date().toISOString(); }
function score(c){
  let s=0; if(c.stars>=400)s+=36; else if(c.stars>=150)s+=26; else if(c.stars>=70)s+=18;
  if(c.lang)s+=6; if(c.license)s+=6; if((c.topics||[]).length>=3)s+=12;
  const d=c.updated_at?(Date.now()-new Date(c.updated_at).getTime())/(86400000):9999; if(d<=60)s+=10;
  if((c.desc||'').length>=20)s+=6; return Math.min(s,100);
}

function main(){
  const cands=load(CAND);
  const done=new Set(load(PUB).map(x=>x.source_url));
  let add=0;
  for(const c of cands){
    if(done.has(c.url)) continue;
    const sc=score(c);
    if(sc<46 && (c.stars||0)<80) continue;
    const a={
      asset_id:`H-AUTO-${Date.now()}-${h(c.url)}`,
      type:'宸ュ叿璧勬簮', name:c.title, desc:c.desc||'', source:'hidden_autoops',
      source_url:c.url, lang:c.lang||'', tags:Array.from(new Set([...(c.topics||[]),'hidden_auto'])).slice(0,12),
      auto_score:sc, status:'auto_published', auto:true, hidden:true,
      published_at:now(), created_at:now()
    };
    append(PUB,a); done.add(c.url); add++;
    append(LOG,{ts:now(), url:c.url, sc, action:'auto_published'});
  }
  episodic('hidden_finder_auto_publish',{added:add, total:load(PUB).length});
  console.log(`[hidden_finder] auto_published=${add}`);
}
main();
