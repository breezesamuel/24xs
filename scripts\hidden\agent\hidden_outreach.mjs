#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { episodic, recall, conversation } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const LEADS = path.join(H, 'leads_auto.jsonl');
const DRAFTS = path.join(H, 'drafts_auto.jsonl');
const SENT = path.join(H, 'outreach_sent_auto.jsonl');
const CRM = path.join(H, 'crm_auto.jsonl');

const MAX_PER_TICK = 3;
const RETRY_DELAY_MS = 30 * 60 * 1000; // 30 min before retry

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function save(p,arr){ fs.writeFileSync(p, arr.map(x=>JSON.stringify(x)).join('\n')+(arr.length?'\n':'')); }
function now(){ return new Date().toISOString(); }

async function ai(prompt){
  const key = process.env.OPENROUTER_API_KEY || process.env.AI_API_KEY || '';
  const base = process.env.AI_BASE_URL || 'https://openrouter.ai/api/v1/chat/completions';
  const model = process.env.AI_MODEL || 'deepseek/deepseek-chat-v3-0324:free';
  if(!key) return { ok:false, reason:'no_key', retryable:true };
  try{
    const res = await fetch(base,{
      method:'POST', headers:{'Authorization':`Bearer ${key}`,'Content-Type':'application/json','HTTP-Referer':'https://app.highkingflower.com','X-Title':'24XS-Hidden-Outreach'},
      body: JSON.stringify({ model, temperature:0.22, max_tokens:240, messages:[{role:'system',content:'浣犳槸鍏ㄨ嚜鍔ㄥ晢鍔″姪鐞嗐€傜敓鎴愭瀬绠€銆佸悎瑙勭殑棣栨娌熼€氳瘽鏈紙<=32瀛楋級銆備笉澶稿ぇ銆佷笉鎵胯銆佷笉鏁忔劅鐢ㄨ銆?},{role:'user',content:prompt}] })
    });
    if(!res.ok){
      const retryable = res.status === 429 || res.status >= 500;
      return { ok:false, reason:`http_${res.status}`, retryable };
    }
    const j = await res.json();
    const txt = j.choices?.[0]?.message?.content?.trim().replace(/\s+/g,' ');
    return { ok:true, text: txt.slice(0,120) };
  }catch(e){ return { ok:false, reason:e.message, retryable:true }; }
}

function canRetry(lead){
  if(!lead.last_outreach_at) return true;
  return Date.now() - new Date(lead.last_outreach_at).getTime() >= RETRY_DELAY_MS;
}

async function main(){
  const leads = load(LEADS).filter(x =>
    (x.stage === 'discovered' || (x.stage === 'outreach_failed' && canRetry(x))) &&
    !x.contacted
  );
  const kn = recall('knowledge',10).map(k=>k.rule).join(' | ');

  const batch = leads.slice(0, MAX_PER_TICK);
  let d=0, s=0, deferred=0;
  const allLeads = load(LEADS);

  for(const l of batch){
    const prompt = `鍘嗗彶缁忛獙锛?{kn||'鏃?}\n绾跨储锛?{l.url}\n璇风敓鎴愪竴鏉″悎瑙勯娆¤瘽鏈紙<=32瀛楋級锛屼粎璋堝彲鑳戒环鍊笺€傚彧杩斿洖璇濇湳銆俙;
    const r = await ai(prompt);
    const ts = now();

    const dr = { id:`HD-${Date.now()}-${d}`, lead_id:l.id, url:l.url, ai_ok:r.ok, text:r.ok?r.text:'', auto:true, sent:r.ok, sent_at:r.ok?ts:undefined, created_at:ts, retryable: r.retryable };
    append(DRAFTS, dr);

    const idx = allLeads.findIndex(x => x.id === l.id);
    if(idx >= 0){
      allLeads[idx].last_outreach_at = ts;
      allLeads[idx].outreach_attempts = (allLeads[idx].outreach_attempts || 0) + 1;

      if(r.ok){
        conversation(l.id, 'auto_outreach', dr.text);
        append(SENT, { sid:`HS-${Date.now()}-${s++}`, lead_id:l.id, text:dr.text, channel:'auto_sim', status:'sent', auto:true, sent_at:ts });
        const crm = load(CRM);
        let rec = crm.find(x => x.lead_id === l.id);
        if(!rec){
          rec = { crm_id:`HCRM-${Date.now()}-${d}`, lead_id:l.id, url:l.url, stage:'contacted', owner:'hidden_auto', priority:'high', timeline:[], auto:true, created_at:ts, updated_at:ts };
          crm.push(rec);
        }
        rec.stage = 'contacted'; rec.timeline.push({ts, act:'auto_contacted', note:'鍏ㄨ嚜鍔ㄥ鍛硷紙妯℃嫙锛?}); rec.updated_at = ts; save(CRM, crm);
        allLeads[idx].contacted = true; allLeads[idx].stage = 'contacted';
        s++;
      }else{
        // Defer - don't mark as contacted, will retry next tick if retryable
        if(r.retryable && allLeads[idx].outreach_attempts < 5){
          allLeads[idx].stage = 'discovered'; // Back to discovered for retry
          deferred++;
        }else{
          allLeads[idx].stage = 'outreach_failed';
        }
      }
    }
    d++;
    await new Promise(r => setTimeout(r, 1500));
  }

  save(LEADS, allLeads);
  episodic('hidden_outreach_auto', {drafted: d, sent: s, deferred, total_pending: leads.length});
  console.log(`[hidden_outreach] ${d} processed, ${s} sent, ${deferred} deferred`);
}
main();