#!/usr/bin/env node
/**
 * select_wheel.mjs — "先检索复用 → 五维筛选 → 安全门禁 → 选3 → 判定 → 评估成本风险" 执行器
 *
 * 【防 AI 幻觉】所有结论只来自 GitHub API 真实元数据，不信任任何搜索摘要：
 *   - 存在性：/repos 返回 404 → 判定为"幻觉仓库"，直接剔除（不参与打分）
 *   - 归档：archived=true → 剔除（不再维护）
 *   - 停更：pushed_at 距今 >730 天 → 剔除；>365 天 → 降权
 *   - 最新版本：/releases/latest（tag + 发布时间），避免"推荐停更/旧版本"
 *   - 安全门禁（新）：/repos/{full}/security-advisories（GHSA）+ OSV.dev 已知漏洞
 *       CRITICAL 公告 → 剔除；HIGH 公告或 ≥5 个 OSV 漏洞 → 封顶 REVIEW（禁止"可直接用"）
 *
 * 五维（全部真实值）：
 *   D1 更新时间(0.18)  D2 Star(0.18)  D3 协议(0.32)  D4 技术栈(0.20)  D5 部署难度(0.12)
 *   安全作为"门禁"而非加权维（避免用高分掩盖漏洞）。
 *
 * 输出：控制台候选表 + 机读报告 standards/wheel_selection_report.json
 *
 * 用法:
 *   node select_wheel.mjs --target crawler --stack python
 *   node select_wheel.mjs --target workflow --stack node
 *   node select_wheel.mjs --target ecommerce --stack node
 *   node select_wheel.mjs --target crawler --stack python --no-security   # 跳过安全查询（离线/限流时）
 */
'use strict';
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../../');
const REPORT = path.join(ROOT, 'standards/wheel_selection_report.json');

/** 令牌解析：优先 GH_TOKEN，其次 gh CLI；缺失则匿名（限流 60/h，仍可用但大概率 403） */
function resolveToken(){
  const env = (process.env.GH_TOKEN || '').trim();
  if(env && !/^(gh[pousr]_)?x{6,}/i.test(env) && env.length > 20) return env;
  try{ return execSync('gh auth token', { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); }catch(e){ return ''; }
}
const TOKEN = resolveToken();
const H = Object.assign(
  { Accept: 'application/vnd.github+json', 'User-Agent': 'autoops-select-wheel', 'X-GitHub-Api-Version': '2022-11-28' },
  TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}
);

const STRONG = new Set(['gpl-2.0', 'gpl-3.0', 'agpl-3.0', 'sspl-1.0', 'osl-3.0', 'eupl-1.2']);
const WEAK = new Set(['lgpl-2.1', 'lgpl-3.0', 'mpl-2.0']);
const PERMISSIVE = new Set(['mit', 'apache-2.0', 'bsd-2-clause', 'bsd-3-clause', 'isc', 'unlicense', '0bsd', 'cc0-1.0']);
const FAIRCODE = new Set(['sustainable-use-license', 'elastic-license-2.0', 'bsl-1.1', 'noassertion-unknown']);

// 候选池（坐标即"检索"结果；真实元数据由 API 回填验证）
const POOLS = {
  crawler: [
    'unclecode/crawl4ai', 'scrapy/scrapy', 'gocolly/colly', 'adbar/trafilatura',
    'mendableai/firecrawl', 'mikf/gallery-dl', 'projectdiscovery/katana',
  ],
  workflow: [
    'temporalio/temporal', 'windmill-labs/windmill', 'kestra-io/kestra',
    'PrefectHQ/prefect', 'dagster-io/dagster', 'hatchet-dev/hatchet', 'n8n-io/n8n', 'apache/airflow',
  ],
  ecommerce: [
    'medusajs/medusa', 'saleor/saleor', 'bagisto/bagisto', 'vendure-ecommerce/vendure',
    'chatwoot/chatwoot', 'frappe/erpnext', 'spree/spree',
  ],
};

// 部署难度人工标注（1=极易 2=易 3=中 4=难 5=很难）
const DEPLOY = {
  'unclecode/crawl4ai': 4, 'scrapy/scrapy': 3, 'gocolly/colly': 2, 'adbar/trafilatura': 1,
  'mendableai/firecrawl': 4, 'mikf/gallery-dl': 1, 'projectdiscovery/katana': 2,
  'temporalio/temporal': 5, 'windmill-labs/windmill': 3, 'kestra-io/kestra': 3,
  'PrefectHQ/prefect': 3, 'dagster-io/dagster': 3, 'hatchet-dev/hatchet': 4, 'n8n-io/n8n': 3, 'apache/airflow': 4,
  'medusajs/medusa': 3, 'saleor/saleor': 4, 'bagisto/bagisto': 3, 'vendure-ecommerce/vendure': 3,
  'chatwoot/chatwoot': 4, 'frappe/erpnext': 5, 'spree/spree': 3,
};

// 包名覆盖（repo → OSV 生态+包名）；用于消除"仓库名≠包名"的误判；未覆盖则按末段名猜测并标注 UNVERIFIED
const PKG = {
  'mendableai/firecrawl': { ecosystem: 'PyPI', name: 'firecrawl-py' },
  'apache/airflow':       { ecosystem: 'PyPI', name: 'apache-airflow' },
  'medusajs/medusa':      { ecosystem: 'npm',  name: '@medusajs/medusa' },
  'unclecode/crawl4ai':   { ecosystem: 'PyPI', name: 'crawl4ai' },
  'adbar/trafilatura':    { ecosystem: 'PyPI', name: 'trafilatura' },
  'mikf/gallery-dl':      { ecosystem: 'PyPI', name: 'gallery-dl' },
  'scrapy/scrapy':        { ecosystem: 'PyPI', name: 'scrapy' },
  'PrefectHQ/prefect':    { ecosystem: 'PyPI', name: 'prefect' },
  'dagster-io/dagster':   { ecosystem: 'PyPI', name: 'dagster' },
  'n8n-io/n8n':           { ecosystem: 'npm',  name: 'n8n' },
};
const ECO_BY_STACK = { python: 'PyPI', node: 'npm', go: 'Go', rust: 'crates.io', php: 'Packagist', java: 'Maven', ruby: 'RubyGems' };

function stackNorm(lang) {
  const l = String(lang || '').toLowerCase();
  if (['python'].includes(l)) return 'python';
  if (['typescript', 'javascript', 'node.js', 'node'].includes(l)) return 'node';
  if (['go'].includes(l)) return 'go';
  if (['rust'].includes(l)) return 'rust';
  if (['java', 'kotlin'].includes(l)) return 'java';
  if (['php'].includes(l)) return 'php';
  if (['ruby'].includes(l)) return 'ruby';
  return 'other';
}

function licenseInfo(spdx) {
  const s = String(spdx || '').toLowerCase();
  if (!s) return { cls: 'UNKNOWN', risk: 'critical', score: 0, note: '未标注许可证 → 默认版权保留，商用即侵权' };
  if (STRONG.has(s)) return { cls: 'STRONG_COPYLEFT', risk: 'critical', score: 0, note: 'GPL/AGPL/SSPL 强传染：闭源商用/自托管 SaaS 可能被迫开源自有代码' };
  if (FAIRCODE.has(s) || s.startsWith('noassertion')) return { cls: 'FAIR_CODE_OR_UNKNOWN', risk: 'high', score: 10, note: 'fair-code(NOASSERTION) 或混合许可：必须人工审查 LICENSE 全文后方可商用' };
  if (WEAK.has(s)) return { cls: 'WEAK_COPYLEFT', risk: 'medium', score: 45, note: 'LGPL/MPL：动态链接安全，对本库的修改须开源' };
  if (PERMISSIVE.has(s)) return { cls: 'PERMISSIVE', risk: 'low', score: 100, note: s === 'apache-2.0' ? 'Apache-2.0 宽松+专利授权（保留 NOTICE）' : 'MIT/BSD/ISC 宽松（保留版权声明）' };
  return { cls: 'OTHER', risk: 'medium', score: 30, note: '需人工审查: ' + s };
}

async function ghJson(url){
  const r = await fetch(url, { headers: H, signal: AbortSignal.timeout(20000) });
  return r;
}

/** 存在性/归档/停更 —— 全部来自 /repos 真实元数据 */
async function fetchRepo(full) {
  let r;
  try{ r = await ghJson(`https://api.github.com/repos/${full}`); }
  catch(e){ return { full, exists: null, err: e.message }; }
  if (r.status === 404) return { full, exists: false };
  if (r.status === 403) return { full, exists: null, err: 'GitHub API 限流(403) — 建议配置 GH_TOKEN' };
  if (!r.ok) return { full, exists: null, err: `GitHub API HTTP ${r.status}` };
  const j = await r.json();
  if (j.archived) return { full, exists: true, archived: true, stars: j.stargazers_count || 0, disabled: !!j.disabled };
  return {
    full, exists: true, archived: !!j.archived, disabled: !!j.disabled,
    stars: j.stargazers_count || 0, forks: j.forks_count || 0,
    lang: j.language || '', license: (j.license && (j.license.spdx_id || j.license.key)) || '',
    pushed_at: j.pushed_at, stale_days: Math.floor((Date.now() - new Date(j.pushed_at).getTime()) / 86400000),
    issues: j.open_issues_count || 0, desc: (j.description || '').slice(0, 80),
    homepage: j.homepage || '', default_branch: j.default_branch || 'main',
  };
}

/** 最新发布版本（防"推荐旧版本/停更版本"） */
async function fetchLatestRelease(full) {
  let r;
  try{ r = await ghJson(`https://api.github.com/repos/${full}/releases/latest`); }
  catch(e){ return { tag: null, note: 'release 查询失败: ' + e.message }; }
  if (r.status === 404) return { tag: null, note: '无 release（可能仅用 tag 或未发布）' };
  if (!r.ok) return { tag: null, note: `release API HTTP ${r.status}` };
  const j = await r.json();
  const age = j.published_at ? Math.floor((Date.now() - new Date(j.published_at).getTime()) / 86400000) : null;
  return { tag: j.tag_name || null, name: (j.name || '').slice(0, 60) || null, published_at: j.published_at || null, age_days: age };
}

/** GitHub 仓库安全公告（GHSA，真实数据库） */
async function fetchAdvisories(full) {
  let r;
  try{ r = await ghJson(`https://api.github.com/repos/${full}/security-advisories?per_page=100`); }
  catch(e){ return { count: null, note: 'advisory 查询失败: ' + e.message }; }
  if (r.status === 404) return { count: null, note: 'advisory API 404（无权限或仓库级公告未开放）' };
  if (!r.ok) return { count: null, note: `advisory API HTTP ${r.status}` };
  const j = await r.json();
  const arr = Array.isArray(j) ? j : [];
  const severities = {};
  arr.forEach(a => { const s = String(a.severity || 'unknown').toLowerCase(); severities[s] = (severities[s] || 0) + 1; });
  return { count: arr.length, severities };
}

/** OSV.dev 已知漏洞（免费、无需鉴权） */
async function fetchOsv(full, stack) {
  const p = PKG[full] || { ecosystem: ECO_BY_STACK[stack], name: (full.split('/')[1] || ''), guessed: true };
  if (!p.ecosystem) return { count: null, note: '生态未知 → 跳过 OSV（UNVERIFIED）' };
  let r;
  try{
    r = await fetch('https://api.osv.dev/v1/query', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ package: { name: p.name, ecosystem: p.ecosystem } }),
      signal: AbortSignal.timeout(15000),
    });
  }catch(e){ return { count: null, note: 'OSV 查询失败: ' + e.message }; }
  if (!r.ok) return { count: null, note: `OSV HTTP ${r.status}` };
  const j = await r.json().catch(() => ({}));
  const vulns = Array.isArray(j.vulns) ? j.vulns : [];
  return {
    count: vulns.length,
    ids: vulns.slice(0, 8).map(v => v.id),
    package: `${p.name}@${p.ecosystem}`,
    guessed: !!p.guessed,
    note: vulns.length ? `${p.name}@${p.ecosystem} 命中 ${vulns.length} 条${p.guessed ? '（包名为推断）' : ''}` : `无已知漏洞（${p.name}@${p.ecosystem}${p.guessed ? '，包名为推断' : ''}）`,
  };
}

/** 安全门禁：公告/漏洞 → 等级（critical 剔除，high 封顶 REVIEW） */
function securityGate(adv, osv) {
  const sev = (adv && adv.severities) || {};
  const crit = sev.critical || 0, high = sev.high || 0;
  const osvCount = (osv && typeof osv.count === 'number') ? osv.count : 0;
  const notes = [];
  let level = 'ok';
  if (crit > 0) { level = 'critical'; notes.push(`GitHub 安全公告 CRITICAL×${crit}`); }
  else if (high > 0) { level = 'high'; notes.push(`GitHub 安全公告 HIGH×${high}`); }
  if (osvCount >= 5) { level = (level === 'critical') ? 'critical' : 'high'; notes.push(`OSV 已知漏洞×${osvCount}`); }
  else if (osvCount > 0) { if (level === 'ok') level = 'medium'; notes.push(`OSV 已知漏洞×${osvCount}`); }
  return { level, notes };
}

function score(r, stack) {
  const days = (r.stale_days === undefined || r.stale_days === null) ? 99999 : r.stale_days;
  const D1 = days <= 30 ? 100 : days <= 180 ? 70 : days <= 365 ? 40 : 0;
  const D2 = r.stars >= 20000 ? 100 : r.stars >= 8000 ? 80 : r.stars >= 2000 ? 60 : r.stars >= 300 ? 35 : 15;
  const li = licenseInfo(r.license);
  const D3 = li.score;
  const match = stackNorm(r.lang) === stack;
  const D4 = match ? 100 : (['node', 'python'].includes(stackNorm(r.lang)) && ['node', 'python'].includes(stack) ? 55 : 15);
  const D5 = 100 - ((DEPLOY[r.full] || 3) - 1) * 22;
  const total = Math.round(D1 * 0.18 + D2 * 0.18 + D3 * 0.32 + D4 * 0.20 + D5 * 0.12);
  return { D1, D2, D3, D4, D5, total, li, match };
}

/** 综合判定：协议红线/归档/停更/安全门禁 优先于加权总分 */
function verdictOf(r, s, sec) {
  if (s.li.risk === 'critical') return 'ELIMINATE(协议红线)';
  if (r.archived) return 'ELIMINATE(已归档)';
  if (r.disabled) return 'ELIMINATE(已禁用)';
  if ((r.stale_days ?? 99999) > 730) return 'ELIMINATE(停更>2年)';
  if (sec.level === 'critical') return 'ELIMINATE(已知严重漏洞)';
  let v = s.D3 >= 100 && (r.stale_days ?? 99999) <= 365 && s.match ? 'DIRECT_USE(可直接用)'
    : s.D3 >= 100 ? 'SUITABLE(可用，需评估二开)'
    : 'REVIEW(人工审查后决定)';
  if (sec.level === 'high' && v.startsWith('DIRECT_USE')) v = 'REVIEW(有高危漏洞，禁止直接复用)';
  return v;
}

(async () => {
  const args = process.argv.slice(2);
  const getArg = k => { const i = args.indexOf('--' + k); return i >= 0 ? args[i + 1] : null; };
  const target = getArg('target') || 'crawler';
  const stack = getArg('stack') || 'python';
  const noSecurity = args.includes('--no-security');
  const pool = POOLS[target];
  if (!pool) { console.error('unknown target. use: ' + Object.keys(POOLS).join('|')); process.exit(1); }

  console.log(`\n=== 目标=${target} 宿主栈=${stack} 候选=${pool.length} token=${TOKEN ? 'OK' : 'ANON(可能限流)'} ===\n`);
  const rows = [];
  const hallucination = [];
  const eliminated = [];

  for (const full of pool) {
    const r = await fetchRepo(full);
    if (r.exists === false) { console.log(`[NOT_FOUND] ${full}  <-- 幻觉仓库（不存在，直接剔除）`); hallucination.push(full); continue; }
    if (r.exists === null) { console.log(`[UNVERIFIED] ${full}: ${r.err}`); continue; }
    if (r.archived) { console.log(`[ARCHIVED]  ${full}  stars=${r.stars}`); eliminated.push({ full, reason: 'archived' }); continue; }
    if (r.disabled) { console.log(`[DISABLED]  ${full}`); eliminated.push({ full, reason: 'disabled' }); continue; }

    const s = score(r, stack);
    // 安全查询：仅对通过存在性/归档的候选执行（节省配额）
    const latest = noSecurity ? { tag: null, note: 'skipped' } : await fetchLatestRelease(full);
    const adv = noSecurity ? { count: null, note: 'skipped' } : await fetchAdvisories(full);
    const osv = noSecurity ? { count: null, note: 'skipped' } : await fetchOsv(full, stack);
    const sec = noSecurity ? { level: 'skipped', notes: ['安全查询已跳过(--no-security)'] } : securityGate(adv, osv);
    const verdict = verdictOf(r, s, sec);

    rows.push({ ...r, ...s, verdict, latest, advisories: adv, osv, security: sec });

    console.log(`${r.full}`);
    console.log(`  D1 更新:${r.stale_days}天(${s.D1})  D2 Star:${r.stars}(${s.D2})  D3 协议:${r.license || 'NONE'}→${s.li.cls}(${s.D3})  D4 栈:${r.lang}${s.match ? '✓' : '✗'}(${s.D4})  D5 部署:${DEPLOY[full]}(难度)→${s.D5}`);
    console.log(`  加权总分: ${s.total} | 判定: ${verdict} | ${s.li.note}`);
    console.log(`  最新版本: ${latest.tag || '无'}${latest.age_days != null ? ` (${latest.age_days}天前)` : ''}  安全: ${sec.level}${sec.notes.length ? ' — ' + sec.notes.join('; ') : ''}`);
    if (s.li.risk !== 'low') console.log(`  ⚠️ 协议风险: ${s.li.note}`);
    console.log('');
  }

  const usable = rows.filter(r => r.verdict.startsWith('DIRECT_USE') || r.verdict.startsWith('SUITABLE'))
    .sort((a, b) => b.total - a.total).slice(0, 3);
  console.log('=== 推荐 Top' + Math.min(3, usable.length) + ' ===');
  usable.forEach((r, i) => {
    console.log(`${i + 1}. ${r.full} (总分 ${r.total}) → ${r.verdict}  [版本 ${r.latest.tag || '-'}]  安全=${r.security.level}`);
    console.log(`   成本: 引入=${D5_TEXT(r)} 维护=${r.stale_days <= 30 ? '低(0-30天活跃)' : r.stale_days <= 180 ? '中' : '高'} 风险=${r.li.risk}`);
  });
  if (!usable.length) console.log('无可安全复用项 → 建议自研（或人工审查清单中的 REVIEW 项）');

  const report = {
    generated_at: new Date().toISOString(),
    target, stack, host_token: !!TOKEN, security_checked: !noSecurity,
    recommended: usable.map(r => ({ full: r.full, total: r.total, verdict: r.verdict, version: r.latest.tag, security: r.security.level })),
    candidates: rows.map(r => ({
      full: r.full, stars: r.stars, forks: r.forks, lang: r.lang, license: r.license || null,
      license_cls: r.li.cls, license_risk: r.li.risk, stale_days: r.stale_days, pushed_at: r.pushed_at,
      D1: r.D1, D2: r.D2, D3: r.D3, D4: r.D4, D5: r.D5, total: r.total, verdict: r.verdict,
      latest_release: r.latest, advisories: r.advisories, osv: r.osv, security: r.security,
    })),
    eliminated, hallucination,
  };
  try{ fs.mkdirSync(path.dirname(REPORT), { recursive: true }); fs.writeFileSync(REPORT, JSON.stringify(report, null, 2)); console.log(`\n[report] 已写入 ${path.relative(ROOT, REPORT)}`); }
  catch(e){ console.error('[report] 写入失败: ' + e.message); }
  console.log('');

  function D5_TEXT(r) { const d = DEPLOY[r.full] || 3; return d <= 2 ? '极低' : d === 3 ? '中' : d >= 4 ? '高(多组件)' : '极高(集群)'; }
})().catch(e => { console.error('FAIL', e.message); process.exit(1); });
