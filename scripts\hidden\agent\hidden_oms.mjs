#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { episodic } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const ORD = path.join(H, 'orders_auto.jsonl');
const AFS = path.join(H, 'aftersale_auto.jsonl');
const CRM = path.join(H, 'crm_auto.jsonl');

const ORDER_DELAY_MS = {
  processing: 60 * 60 * 1000,    // 1 hour to shipped
  shipped: 4 * 60 * 60 * 1000,   // 4 hours to delivered
  delivered: 24 * 60 * 60 * 1000 // 24 hours to completed
};

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function save(p,arr){ fs.writeFileSync(p, arr.map(x=>JSON.stringify(x)).join('\n')+(arr.length?'\n':'')); }
function now(){ return new Date().toISOString(); }

function getLastEventTime(obj, actPrefix){
  return obj.timeline?.findLast?.(e => e.act?.startsWith(actPrefix))?.ts || obj.updated_at || obj.created_at;
}

function canAdvanceOrder(o, status, ts){
  const last = getLastEventTime(o, 'auto_');
  return Date.now() - new Date(last).getTime() >= ORDER_DELAY_MS[status];
}

function main(){
  const ord=load(ORD); const ts=now();
  let sh=0, dl=0, cp=0, af=0;
  for(const o of ord){
    if(o.status==='processing' && o.logistics?.status==='processing' && canAdvanceOrder(o, 'processing', ts)){
      o.status='shipped'; o.logistics.status='shipped';
      o.logistics.events.push({ts,act:'auto_shipped'});
      o.timeline.push({ts,act:'auto_shipped'});
      o.updated_at=ts; sh++;
    }else if(o.status==='shipped' && o.logistics?.status==='shipped' && canAdvanceOrder(o, 'shipped', ts)){
      o.status='delivered'; o.logistics.status='delivered';
      o.logistics.events.push({ts,act:'auto_delivered'});
      o.timeline.push({ts,act:'auto_delivered'});
      o.updated_at=ts; dl++;
      // Open aftersale (not auto-close immediately)
      append(AFS,{ tid:`HAF-${Date.now()}-${af++}`, order_id:o.order_id, crm_id:o.crm_id, status:'open', auto:true, issue:'鑷姩鍞悗璺熻繘', solution:'', timeline:[{ts,act:'auto_opened'}], created_at:ts });
    }else if(o.status==='delivered' && canAdvanceOrder(o, 'delivered', ts)){
      o.status='completed'; o.timeline.push({ts,act:'auto_completed'}); o.updated_at=ts; cp++;
      // Auto-close aftersale after completion
      const afs=load(AFS);
      for(const a of afs){ if(a.order_id===o.order_id && a.status==='open'){ a.status='closed'; a.solution='绯荤粺鑷姩宸℃闂幆'; a.timeline.push({ts,act:'auto_resolved'},{ts,act:'auto_closed'}); a.closed_at=ts; } }
      save(AFS,afs);
    }
  }
  save(ORD,ord);

  // Sync CRM stage
  const crm=load(CRM);
  for(const c of crm){
    if(c.stage==='won'){
      const has=ord.find(x=>x.crm_id===c.crm_id && (x.status==='shipped'||x.status==='delivered'||x.status==='completed'));
      if(has){ c.stage='fulfilled'; c.timeline.push({ts,act:'auto_fulfilled'}); c.updated_at=ts; }
    }
  }
  save(CRM,crm);
  episodic('hidden_oms_auto',{shipped:sh,delivered:dl,completed:cp,aftersale:af});
  console.log(`[hidden_oms] sh=${sh} dl=${dl} cp=${cp} af=${af}`);
}
main();