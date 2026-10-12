#!/usr/bin/env node
/**
 * restore_from_github.mjs — 从 GitHub API 全量恢复本地被回滚的代码文件
 * 起因：本地 `git checkout -- .` / stash 操作把已跟踪文件的修改回滚到旧的 commit，
 * 而 GitHub（breezesamuel/24xs main）才是经过验证的线上版本。
 * 只读 GitHub → 覆盖本地；不动 autoops/hidden/ 运行数据（未跟踪文件不受影响）。
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath, pathToFileURL } from 'url';
import { execSync } from 'child_process';

const REPO = 'breezesamuel/24xs';
const BRANCH = 'main';

// 动态解析 ROOT（不硬编码）
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../..');

// 需恢复的路径（目录递归）
const TARGETS = [
  'scripts/hidden',
  '.github/workflows',
  'api',
  'autoops_status.mjs',
  'AUDIT_REPORT.md',
  'AUDIT_REPORT_PHASE2.md',
  '.gitignore',
  'vercel.json',
];

let restored = 0, failed = 0;

function getToken() {
  return process.env.GH_TOKEN || execSync('gh auth token', { encoding: 'utf8' }).trim();
}

const H = () => ({
  Authorization: `Bearer ${getToken()}`,
  Accept: 'application/vnd.github+json',
  'User-Agent': 'restore-from-github'
});

async function listDir(p) {
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${p}?ref=${BRANCH}`, { headers: H() });
    if (r.status === 404) return null;
    if (r.status === 403) throw new Error('GitHub API 403（限流），请配置真实 GH_TOKEN 后重试');
    return await r.json();
  } catch (e) {
    if (e.message.includes('403')) throw e;
    return null;
  }
}

async function restore(p) {
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${p}?ref=${BRANCH}`, { headers: H(), signal: AbortSignal.timeout(20000) });
    if (!r.ok) { console.log(`MISS  ${p} (http ${r.status})`); failed++; return; }
    const j = await r.json();
    const buf = Buffer.from(j.content || '', 'base64');
    const local = path.join(ROOT, p);
    fs.mkdirSync(path.dirname(local), { recursive: true });
    fs.writeFileSync(local, buf);
    restored++;
    console.log(`OK    ${p} (${buf.length}B)`);
  } catch (e) { console.log(`ERR   ${p} ${e.message}`); failed++; }
}

async function walk(p) {
  const items = await listDir(p);
  if (items === null) { console.log(`MISS-DIR ${p}`); return; }
  for (const it of items) {
    if (it.type === 'dir') await walk(p + '/' + it.name);
    else if (it.type === 'file') await restore(p + '/' + it.name);
  }
}

async function main() {
  for (const t of TARGETS) {
    const probe = await listDir(t);
    if (Array.isArray(probe)) await walk(t);
    else if (probe && probe.type === 'file') await restore(t);
    else await walk(t);
  }
  console.log(`\n=== 恢复完成: ${restored} 个文件, 失败 ${failed} ===`);
  console.log('提示: 如仍有缺漏，请先配置真实 GH_TOKEN 再运行本脚本。');
}

if(process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href){
  main().catch(e => { console.error('FAIL', e.message); process.exit(1); });
}