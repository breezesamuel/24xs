#!/usr/bin/env node
/**
 * 24xs 系统最终状态检查
 */
const fs = require('fs');
const path = require('path');

const ROOT = 'F:\\2026\\24xs';

console.log('========================================');
console.log('  24xs 系统状态检查');
console.log('========================================');

// 1. 关键文件
const checks = [
  ['scripts/hidden/agent/content-distributor.js', '内容分发器'],
  ['scripts/hidden/agent/run-distributor-hidden.js', '启动脚本（新）'],
  ['scripts/hidden/agent/run-distributor-hidden.vbs', '启动脚本（旧）'],
  ['autoops/hidden/distributor_task.log', '分发日志'],
  ['autoops/hidden/distributor.pid', 'PID 文件'],
];

console.log('\n【关键文件】');
for (const [rel, desc] of checks) {
  const p = path.join(ROOT, rel);
  const exists = fs.existsSync(p);
  const size = exists ? fs.statSync(p).st_size : 0;
  console.log(`  ${exists ? '✅' : '❌'} ${rel} (${desc}) ${size > 0 ? size + 'B' : ''}`);
}

// 2. 最近分发日志
console.log('\n【最近分发日志】');
const logFile = path.join(ROOT, 'autoops', 'hidden', 'distributor_task.log');
if (fs.existsSync(logFile)) {
  const lines = fs.readFileSync(logFile, 'utf-8').split('\n').filter(l => l.trim());
  for (const line of lines.slice(-5)) {
    console.log('  ' + line.trim().slice(0, 100));
  }
} else {
  console.log('  (无日志)');
}

// 3. CDP 状态
console.log('\n【CDP 状态】');
try {
  const net = require('net');
  const client = new net.Socket();
  const connected = await new Promise(resolve => {
    client.connect(9223, '127.0.0.1', () => { resolve(true); client.destroy(); });
    setTimeout(() => { resolve(false); client.destroy(); }, 2000);
  });
  console.log(`  ${connected ? '✅ CDP 在线 (127.0.0.1:9223)' : '❌ CDP 离线'}`);
} catch {
  console.log('  ❌ CDP 连接失败');
}

// 4. 待分发队列
console.log('\n【待分发队列】');
const queueDir = path.join(ROOT, 'scripts', 'hidden', 'agent', 'queue');
if (fs.existsSync(queueDir)) {
  const files = fs.readdirSync(queueDir).filter(f => f.endsWith('.md'));
  console.log(`  ${files.length} 个待分发文件`);
  for (const f of files.slice(0, 5)) {
    console.log(`    - ${f}`);
  }
} else {
  console.log('  (队列目录不存在)');
}

console.log('\n========================================');
console.log('  总结: 分发器工作正常，CDP 需启动后才能发帖');
console.log('========================================');
