#!/usr/bin/env node
/**
 * 检查并更新 24xs 计划任务，将 VBScript 替换为 Node.js 脚本
 */
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = 'F:\\2026\\24xs';
const OLD_VBS = path.join(ROOT, 'scripts\\hidden\\agent\\run-distributor-hidden.vbs');
const NEW_JS = path.join(ROOT, 'scripts\\hidden\\agent\\run-distributor-hidden.js');

console.log('=== 检查计划任务 ===');

// 查当前计划任务
try {
  const out = execSync('schtasks /query /fo LIST /v', { encoding: 'utf-8', timeout: 15000 });
  const tasks = out.split('========================================').filter(s => s.includes('Distributor') || s.includes('distributor'));
  console.log(`找到 ${tasks.length} 个相关任务`);
  for (const t of tasks) {
    console.log(t.slice(0, 300));
  }
} catch (e) {
  console.log('查任务失败:', e.message.slice(0, 200));
}

// 检查旧 VBS 和新 JS 文件
console.log('\n=== 文件检查 ===');
console.log(`旧 VBS: ${OLD_VBS} ${fs.existsSync(OLD_VBS) ? '✅' : '❌'}`);
console.log(`新 JS:  ${NEW_JS}  ${fs.existsSync(NEW_JS) ? '✅' : '❌'}`);

// 列出 hidden/agent 目录
console.log('\n=== scripts/hidden/agent/ 目录 ===');
const agentDir = path.join(ROOT, 'scripts\\hidden\\agent');
try {
  const files = fs.readdirSync(agentDir);
  for (const f of files) {
    const stat = fs.statSync(path.join(agentDir, f));
    console.log(`  ${f}  (${stat.size} bytes)`);
  }
} catch (e) {
  console.log('读目录失败:', e.message);
}

console.log('\n下一步: 手动更新计划任务或直接删掉旧 VBS');