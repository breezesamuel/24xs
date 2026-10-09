#!/usr/bin/env node
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';
import { episodic, profile, target } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const LEADS = path.join(H, 'leads_auto.jsonl');
const POOL = path.join(H, 'lead_pool.jsonl');
const CAND = path.join(H, 'candidates.jsonl');

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function h(s){ return crypto.createHash('sha256').update(String(s)).digest('hex').slice(0,12); }
function now(){ return new Date().toISOString(); }

function extractLeadsFromCandidates(cands){
  const leads = [];
  for(const c of cands){
    // High-star repos -> potential enterprise users
    if(c.stars >= 200){
      leads.push({
        type: 'high_star_repo',
        url: c.url,
        title: `${c.title} (${c.stars}猸?`,
        reason: `High-star repo (${c.stars} stars) - potential enterprise/data team`,
        score: Math.min(50 + c.stars / 10, 100)
      });
    }
    // Repo owners/orgs as leads
    const ownerUrl = `https://github.com/${c.title.split('/')[0]}`;
    leads.push({
      type: 'repo_owner',
      url: ownerUrl,
      title: `${c.title.split('/')[0]} (owner of ${c.title})`,
      reason: `Organization/user owning relevant repo`,
      score: 40
    });
  }
  return leads;
}

function main(){
  const cands = load(CAND);
  const existingLeads = load(LEADS);
  const existingUrls = new Set(existingLeads.map(x => x.url));

  const discoveredLeads = extractLeadsFromCandidates(cands);
  let add = 0;

  for(const lead of discoveredLeads){
    if(existingUrls.has(lead.url)) continue;
    if(lead.score < 45) continue; // Minimum threshold

    const id = `L-${Date.now()}-${h(lead.url)}`;
    const rec = {
      id,
      url: lead.url,
      title: lead.title,
      type: lead.type,
      stage: 'discovered',
      ai_summary: lead.reason,
      lead_score: lead.score,
      drafted: false,
      contacted: false,
      auto: true,
      created_at: now()
    };
    append(LEADS, rec);
    append(POOL, {id, url: lead.url, ts: now(), source: 'crawler', score: lead.score});
    profile(lead.url, {lead_id: id, score: lead.score});
    target({type: 'lead_discovered', url: lead.url, reason: lead.reason, score: lead.score});
    add++;
    existingUrls.add(lead.url);
  }

  episodic('hidden_leads_auto', {added: add, scanned_candidates: cands.length});
  console.log(`[hidden_leads] ${add} new leads from ${cands.length} candidates`);
}
main();