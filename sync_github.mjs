#!/usr/bin/env node
// 用 gh auth token 直接调 GitHub Contents API 同步增强文件
import fs from 'fs';
import { execSync } from 'child_process';

const REPO = 'breezesamuel/24xs';
const BRANCH = 'main';

let token;
try {
  token = execSync('gh auth token', { encoding: 'utf8' }).trim();
} catch (e) {
  console.error('gh auth token 失败:', e.message);
  process.exit(1);
}

async function getSha(repoPath) {
  try {
    const res = await fetch(`https://api.github.com/repos/${REPO}/contents/${repoPath}?ref=${BRANCH}`, {
      headers: { Authorization: `Bearer ${token}`, 'User-Agent': '24xs-sync', 'Accept': 'application/vnd.github+json' }
    });
    if (!res.ok) return null;
    const data = await res.json();
    return data.sha || null;
  } catch (e) { return null; }
}

async function upload(localPath, repoPath, message) {
  if (!fs.existsSync(localPath)) {
    console.log(`  [跳过] 本地不存在: ${localPath}`);
    return;
  }
  // 读取原始字节，统一转 LF，再 base64
  let raw = fs.readFileSync(localPath);
  let text = raw.toString('utf8').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const b64 = Buffer.from(text, 'utf8').toString('base64');
  const sha = await getSha(repoPath);

  const body = { message, content: b64, branch: BRANCH };
  if (sha) body.sha = sha;

  const res = await fetch(`https://api.github.com/repos/${REPO}/contents/${repoPath}`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token}`,
      'User-Agent': '24xs-sync',
      'Content-Type': 'application/json',
      'Accept': 'application/vnd.github+json'
    },
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (res.ok) {
    console.log(`  [OK] ${repoPath} (${sha ? '更新' : '新增'})`);
  } else {
    console.log(`  [失败] ${repoPath}: ${data.message || res.status}`);
  }
}

const files = [
  ['scripts/hidden/agent/hidden_pay.mjs',    'feat: add payment gateway abstraction (hidden_pay) - alipay/moltspay/x402 fail-closed'],
  ['api/internal/hidden/webhook.js',         'feat: add payment callback webhook endpoint (fail-closed verify)'],
  ['scripts/hidden/crawler/hidden_crawler.mjs', 'feat(crawler): multi-source discovery - topics + trending + more keywords'],
  ['scripts/hidden/agent/hidden_leads.mjs',  'feat(leads): multi-dimension scoring + hot/warm/cold grading'],
  ['vercel.json',                            'fix(vercel): enable serverless functions build + webhook route'],
];

console.log(`=== 同步增强到 ${REPO} (branch=${BRANCH}) ===`);
for (const [p, msg] of files) {
  await upload(p, p, msg);
}
console.log('=== 完成 ===');
