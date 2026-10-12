#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { episodic, fact } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const CRM = path.join(H, 'crm_auto.jsonl');
const ORD = path.join(H, 'orders_auto.jsonl');

const STAGE_DELAY_MS = {
  contacted: 30 * 60 * 1000,
  interested: 45 * 60 * 1000,
  quoted: 60 * 60 * 1000,
  negotiating: 90 * 60 * 1000
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
  let mv=0;
  for(const c of crm){
    // 仅推进阶段（标记为模拟），不自动生成订单
    // 真实订单由 hidden_realops.ingestOrders 基于 real_storefront 数据写入 orders_auto.jsonl
    if(c.stage==='contacted' && canAdvance(c, 'contacted', ts)){
      c.stage='interested'; c.timeline.push({ts,act:'auto_mark_interested', note:'模拟推进'}); c.updated_at=ts; mv++;
    }else if(c.stage==='interested' && canAdvance(c, 'interested', ts)){
      c.stage='quoted'; c.timeline.push({ts,act:'auto_quoted', note:'模拟推进'}); c.updated_at=ts; mv++;
    }else if(c.stage==='quoted' && canAdvance(c, 'quoted', ts)){
      c.stage='negotiating'; c.timeline.push({ts,act:'auto_negotiating', note:'模拟推进'}); c.updated_at=ts; mv++;
    }else if(c.stage==='negotiating' && !c.won_auto && canAdvance(c, 'negotiating', ts)){
      c.stage='won'; c.won_auto=true; c.timeline.push({ts,act:'auto_won', note:'模拟推进（无真实支付，不生成订单）'}); c.updated_at=ts; mv++;
      // 不再自动生成 HORD- 订单（避免计时器造单）
      // 真实订单仅来自 hidden_realops 基于 real_storefront paid 状态
    }
  }
  save(CRM,crm);
  episodic('hidden_crm_auto',{moved:mv, orders:0, note:'no auto order creation'});
  console.log(`[hidden_crm] mv=${mv} ord=0 (auto order creation disabled)`);
}

if(process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href){ main(); }