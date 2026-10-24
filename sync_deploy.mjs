#!/usr/bin/env node
// 同步增强文件到 deploy-full（Vercel 部署源）
import fs from 'fs';
import path from 'path';

const SRC = 'F:/2026/24xs';
const DST = 'C:/bingdashan/deploy-full';

const files = [
  'scripts/hidden/agent/hidden_pay.mjs',
  'api/internal/hidden/webhook.js',
  'scripts/hidden/crawler/hidden_crawler.mjs',
  'scripts/hidden/agent/hidden_leads.mjs',
  'vercel.json',
];

console.log(`=== 同步增强到 deploy-full (${DST}) ===`);
for (const rel of files) {
  const src = path.join(SRC, rel);
  const dst = path.join(DST, rel);
  if (!fs.existsSync(src)) {
    console.log(`  [跳过] 源不存在: ${rel}`);
    continue;
  }
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.copyFileSync(src, dst);
  console.log(`  [OK] ${rel}`);
}
console.log('=== 完成 ===');
