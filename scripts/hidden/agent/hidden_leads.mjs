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

// 多维度评分（0-100）：热度 + 话题匹配 + 商业许可 + 语言生态 + 近期活跃
const HOT_TOPICS = ['mcp','ai-agent','automation','data-pipeline','llm-tools','api-tools'];
const BIZ_FRIENDLY = ['mit','apache-2.0','bsd-2-clause','bsd-3-clause','isc'];
const HOT_LANGS = ['python','typescript','javascript','go','rust'];

function scoreRepo(c){
  let s = 0;
  s += Math.min((c.stars||0) / 25, 40);                                  // 热度（最多40）
  const topics = (c.topics||[]).map(t=>String(t).toLowerCase());
  const hits = topics.filter(t => HOT_TOPICS.includes(t)).length;
  s += Math.min(hits * 6, 25);                                           // 话题匹配（最多25）
  const lic = String(c.license||'').toLowerCase();
  if(BIZ_FRIENDLY.some(b => lic.includes(b))) s += 15;                   // 商业友好许可（最多15）
  else if(lic) s += 5;
  if(HOT_LANGS.includes(String(c.lang||'').toLowerCase())) s += 10;      // 语言生态（最多10）
  if(c.updated_at){                                                       // 近期活跃（最多10）
    const days = (Date.now() - new Date(c.updated_at).getTime()) / 86400000;
    if(days < 7) s += 10; else if(days < 30) s += 6; else if(days < 90) s += 3;
  }
  return Math.round(Math.min(s, 100));
}

function gradeLead(score){
  if(score >= 75) return 'hot';
  if(score >= 55) return 'warm';
  return 'cold';
}

function extractLeadsFromCandidates(cands){
  const leads = [];
  for(const c of cands){
    // 高价值仓库（潜在企业/数据团队客户）
    if((c.stars||0) >= 100){
      const score = scoreRepo(c);
      leads.push({
        type: 'high_value_repo',
        url: c.url,
        title: `${c.title} (${c.stars}⭐)`,
        reason: `High-value repo (${c.stars} stars, score ${score}) - potential enterprise/data team`,
        score,
        grade: gradeLead(score)
      });
    }
    // 仓库所属组织/用户（决策者线索）
    const owner = c.title.split('/')[0];
    const ownerUrl = `https://github.com/${owner}`;
    const oScore = Math.max(35, Math.min(50 + ((c.stars||0)/50), 70));
    leads.push({
      type: 'repo_owner',
      url: ownerUrl,
      title: `${owner} (owner of ${c.title})`,
      reason: `Organization/user owning relevant repo (score ${Math.round(oScore)})`,
      score: Math.round(oScore),
      grade: gradeLead(oScore)
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
      grade: lead.grade,
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