#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { episodic, fact } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const CRM = path.join(H, 'crm_auto.jsonl');
const ORD = path.join(H, 'orders_auto.jsonl');

const STAGE_DELAY_MS = {
  contacted: 30 * 60 * 1000,      // 30 min to interested
  interested: 45 * 60 * 1000,     // 45 min to quoted
  quoted: 60 * 60 * 1000,         // 1 hour to negotiating
  negotiating: 90 * 60 * 1000     // 1.5 hours to won
};

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function save(p,arr){ fs.writeFileSync(p, arr.map(x=>JSON.stringify(x)).join('\n')+(arr.length?'\n':'')); }
function now(){ return new Date().toISOString(); }

function canAdvance(c, stage, ts){
  const last = c.timeline?.findLast?.(e => e.act?.startsWith('auto_'))?.ts || c.updated_at || c.created_at;
  return Date.now() - new Date(last).getTime() >= STAGE_DELAY_MS[stage];
}

function main(){
  const crm=load(CRM); const ts=now();
  let mv=0, ord=0;
  for(const c of crm){
    if(c.stage==='contacted' && canAdvance(c, 'contacted', ts)){
      c.stage='interested'; c.timeline.push({ts,act:'auto_mark_interested'}); c.updated_at=ts; mv++;
    }else if(c.stage==='interested' && canAdvance(c, 'interested', ts)){
      c.stage='quoted'; c.timeline.push({ts,act:'auto_quoted'}); c.updated_at=ts; mv++;
    }else if(c.stage==='quoted' && canAdvance(c, 'quoted', ts)){
      c.stage='negotiating'; c.timeline.push({ts,act:'auto_negotiating'}); c.updated_at=ts; mv++;
    }else if(c.stage==='negotiating' && !c.won_auto && canAdvance(c, 'negotiating', ts)){
      c.stage='won'; c.won_auto=true; c.timeline.push({ts,act:'auto_won'}); c.updated_at=ts; mv++;
      const o={ order_id:`HORD-${Date.now()}-${ord}`, crm_id:c.crm_id, lead_id:c.lead_id, status:'processing', auto:true, auto_confirmed:true, logistics:{carrier:'auto', tracking_no:`HTN-${Date.now()}-${Math.random().toString(36).slice(2,6)}`, status:'processing', events:[]}, timeline:[{ts,act:'auto_created'}], created_at:ts, updated_at:ts };
      append(ORD,o); fact(`horder_${o.order_id}`, {crm_id:c.crm_id}, 'hidden_oms'); ord++;
    }
  }
  save(CRM,crm);
  episodic('hidden_crm_auto',{moved:mv, orders:ord});
  console.log(`[hidden_crm] mv=${mv} ord=${ord}`);
}
main();