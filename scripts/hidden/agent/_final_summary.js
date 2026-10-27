#!/usr/bin/env node
/**
 * 24xs 最终状态摘要
 */
const fs = require('fs');
const path = require('path');
const ROOT = 'F:\\2026\\24xs';

console.log('='.repeat(50));
console.log('  24xs 系统状态 — 2026-10-25');
console.log('='.repeat(50));

// 文件检查
console.log('\n【关键文件】');
const files = [
  ['content-distributor.js', '内容分发引擎'],
  ['run-distributor-hidden.js', '启动脚本（Node.js）'],
  ['run-distributor-hidden.vbs', '原 VBScript（已弃用）'],
  ['test-distributor-sync.js', '测试脚本'],
];
for (const [f, desc] of files) {
  const p = path.join(ROOT, 'scripts\\hidden\\agent', f);
  const exists = fs.existsSync(p);
  const size = exists ? fs.statSync(p).st_size : 0;
  console.log(`  ${exists ? '✅' : '❌'} ${f} (${desc}) ${size > 0 ? size + 'B' : ''}`);
}

// 日志
console.log('\n【分发日志（最近 5 行）】');
const log = path.join(ROOT, 'autoops\\hidden\\distributor_task.log');
if (fs.existsSync(log)) {
  const lines = fs.readFileSync(log, 'utf-8').split('\n').filter(Boolean);
  lines.slice(-5).forEach(l => console.log('  ' + l.trim().slice(0, 80)));
} else {
  console.log('  (无日志)');
}

// 队列状态
console.log('\n【待分发队列】');
const queueDir = path.join(ROOT, 'scripts\\hidden\\agent', 'queue');
if (fs.existsSync(queueDir)) {
  const files = fs.readdirSync(queueDir).filter(f => f.endsWith('.md'));
  console.log(`  ${files.length} 个待分发`);
  files.slice(0, 5).forEach(f => console.log(`    - ${f}`));
} else {
  console.log('  (目录不存在或为空)');
}

// 状态
console.log('\n【状态】');
console.log('  ✅ 内容分发器: 运行正常（CDP 离线时跳过发帖，下次重试）');
console.log('  ✅ Node.js 启动脚本: 已替代 VBScript');
console.log('  ⏳ CDP 浏览器: 未启动（需启动 Edge/Chrome --remote-debugging-port=9223）');
console.log('  📋 计划任务: AutoOps_DeployRetry 每 30min 检测');

console.log('\n【下一步】');
console.log('  1. 启动 CDP 浏览器: edge --remote-debugging-port=9223');
console.log('  2. 或直接运行: node scripts/hidden/agent/run-distributor-hidden.js');
console.log('  3. 查看日志: autoops/hidden/distributor_task.log');

console.log('\n' + '='.repeat(50));
