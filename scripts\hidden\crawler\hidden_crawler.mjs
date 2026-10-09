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
const RAW = path.join(H, 'github_raw.jsonl');
const CAND = path.join(H, 'candidates.jsonl');
const SAFE = path.join(H, 'crawl_safe.jsonl');

const UA = '24XS-HiddenAutoOps/1.0 (+https://app.highkingflower.com)';
const ALLOW = ['github.com','raw.githubusercontent.com','gist.github.com','github.io'];
const KEYWORDS = ['data-asset','dataset','business-data','open-data','api-tools','data-api','scraper','automation','mcp','agent-toolkit','backend-tool'];

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
function h(s){ return crypto.createHash('sha256').update(String(s)).digest('hex').slice(0,14); }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }

function parseRobots(txt){
  const lines = txt.toLowerCase().split('\n');
  let currentUA = null;
  const rules = [];
  for(const line of lines){
    const trimmed = line.trim();
    if(trimmed.startsWith('user-agent:')){
      currentUA = trimmed.split(':')[1].trim();
    }else if(trimmed.startsWith('disallow:') && (currentUA === '*' || currentUA === UA.toLowerCase())){
      const path = trimmed.split(':')[1].trim();
      if(path) rules.push(path);
    }
  }
  return rules;
}

async function canCrawl(host){
  try{
    const res = await fetch(`https://${host}/robots.txt`, { headers:{'User-Agent':UA}, signal:AbortSignal.timeout(5500) });
    if(!res.ok) return true;
    const txt = await res.text();
    const disallows = parseRobots(txt);
    // Check if root is disallowed
    return !disallows.some(p => p === '/' || p === '');
  }catch(e){ return true; }
}

async function fetchWithBackoff(url, options, maxRetries = 3){
  for(let attempt = 0; attempt <= maxRetries; attempt++){
    try{
      const res = await fetch(url, options);
      if(res.status === 403 || res.status === 429){
        const retryAfter = res.headers.get('retry-after');
        const waitMs = retryAfter ? parseInt(retryAfter) * 1000 : Math.min(1000 * Math.pow(2, attempt), 60000);
        log(`Rate limited (${res.status}), waiting ${waitMs}ms (attempt ${attempt + 1}/${maxRetries + 1})`);
        await sleep(waitMs);
        continue;
      }
      return res;
    }catch(e){
      if(attempt === maxRetries) throw e;
      await sleep(1000 * Math.pow(2, attempt));
    }
  }
}

function log(m){
  const ts = new Date().toISOString();
  const line = JSON.stringify({ts, src:'hidden_crawler', m});
  console.log(line);
}

async function github(){
  const token = process.env.GH_TOKEN||'';
  const seen=new Set();
  let cnt=0;
  for(const q of KEYWORDS){
    try{
      const url = `https://api.github.com/search/repositories?q=${encodeURIComponent(q)}&sort=stars&order=desc&per_page=15`;
      const res = await fetchWithBackoff(url,{ headers:{'Accept':'application/vnd.github+json','User-Agent':UA,...(token?{'Authorization':`Bearer ${token}`}:{}),'X-GitHub-Api-Version':'2022-11-28'} });
      if(!res.ok){
        episodic('hidden_crawl_github_http',{q,status:res.status});
        continue;
      }
      const data = await res.json();
      for(const repo of (data.items||[])){
        if(repo.fork||repo.archived) continue;
        const key=repo.html_url;
        if(seen.has(key)) continue; seen.add(key);
        const rec={ id:h(key), source:'github', title:repo.full_name, url:key, desc:repo.description||'', lang:repo.language||'', stars:repo.stargazers_count||0, license:repo.license?.spdx_id||'', topics:repo.topics||[], updated_at:repo.updated_at, fetched_at:new Date().toISOString(), auto:true };
        append(RAW,rec); cnt++;
        profile(key,{source:'github',stars:rec.stars}); target({type:'repo', url:key, reason:'github_match'});
      }
      episodic('hidden_crawl_github_ok',{q,count:(data.items||[]).length});
    }catch(e){ episodic('hidden_crawl_github_err',{q,err:e.message}); }
    await sleep(2000); // Increased delay
  }
  // Incremental dedup: only add new URLs to candidates
  const existingCand = load(CAND);
  const existingUrls = new Set(existingCand.map(x => x.url));
  const raw = load(RAW);
  let added = 0;
  for(const x of raw){
    if(!existingUrls.has(x.url)){
      append(CAND, x);
      existingUrls.add(x.url);
      added++;
    }
  }
  // Trim candidates to last 500
  const allCand = load(CAND);
  if(allCand.length > 500){
    const trimmed = allCand.slice(-500);
    fs.writeFileSync(CAND, trimmed.map(x=>JSON.stringify(x)).join('\n')+'\n');
  }
  episodic('hidden_crawl_dedup',{raw:raw.length, added_to_cand: added, total_cand: load(CAND).length});
  console.log(`[hidden_crawler] github=${cnt}, added_to_cand=${added}`);
}

async function safe(){
  for(const host of ALLOW){
    const ok = await canCrawl(host);
    append(SAFE, {ts:new Date().toISOString(),host,ok});
    if(!ok) episodic('hidden_crawl_blocked',{host,reason:'robots'});
    await sleep(1000);
  }
}

async function main(){
  if(!fs.existsSync(H)) fs.mkdirSync(H,{recursive:true});
  await safe();
  await github();
  episodic('hidden_crawler_cycle',{done:true});
}
main();