#!/usr/bin/env node
/**
 * 内容分发队列调度器（同步版，用于测试）
 */
'use strict';

const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = 'F:\\2026\\24xs';
const SCRIPT = path.join(ROOT, 'scripts\\hidden\\agent\\content-distributor.js');
const LOG_DIR = path.join(ROOT, 'autoops', 'hidden');
const LOG_FILE = path.join(LOG_DIR, 'distributor_task.log');

if (!fs.existsSync(LOG_DIR)) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  fs.appendFileSync(LOG_FILE, line, 'utf-8');
  console.log(line.trim());
}

log('Distributor 启动（同步模式）');

if (!fs.existsSync(SCRIPT)) {
  log(`❌ 脚本不存在: ${SCRIPT}`);
  process.exit(1);
}

const result = spawnSync(process.execPath, [SCRIPT, 'run-schedule', '1'], {
  cwd: ROOT,
  encoding: 'utf-8',
  maxBuffer: 10 * 1024 * 1024,
  timeout: 300000, // 5 分钟超时
});

if (result.error) {
  log(`❌ 执行失败: ${result.error.message}`);
  process.exit(1);
}

if (result.status !== 0) {
  log(`⚠️  退出码 ${result.status}`);
  if (result.stderr) log(`stderr: ${result.stderr.slice(0, 500)}`);
} else {
  log('✅ 完成');
}

if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
