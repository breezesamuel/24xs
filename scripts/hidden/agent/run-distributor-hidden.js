#!/usr/bin/env node
/**
 * 内容分发队列调度器（静默版）
 * 替代原 VBScript run-distributor-hidden.vbs
 * 无窗口静默运行，日志写入 distributor_task.log
 * 由计划任务或 node cron 每 30 分钟调用
 */
'use strict';

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = 'F:\\2026\\24xs';
const SCRIPT = path.join(ROOT, 'scripts\\hidden\\agent\\content-distributor.js');
const LOG_DIR = path.join(ROOT, 'autoops', 'hidden');
const LOG_FILE = path.join(LOG_DIR, 'distributor_task.log');

// 确保日志目录存在
if (!fs.existsSync(LOG_DIR)) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
}

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  fs.appendFileSync(LOG_FILE, line, 'utf-8');
  process.stdout.write(line);
}

log('Distributor 启动');

// 检查脚本是否存在
if (!fs.existsSync(SCRIPT)) {
  log(`❌ 脚本不存在: ${SCRIPT}`);
  process.exit(1);
}

// 用 spawn 静默执行（detached + no window）
const child = spawn(process.execPath, [SCRIPT, 'run-schedule', '1'], {
  cwd: ROOT,
  detached: true,
  stdio: ['ignore', 'ignore', 'ignore'],
  windowsHide: true,
});

child.unref(); // 不等待子进程，立即退出
log(`✅ 已启动 content-distributor.js PID=${child.pid}`);

// 写 PID 文件供守护进程监控
const pidFile = path.join(LOG_DIR, 'distributor.pid');
fs.writeFileSync(pidFile, String(child.pid), 'utf-8');

process.exit(0);
