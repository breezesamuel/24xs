#!/usr/bin/env node
/**
 * 手动设置内容分发计划任务（无需管理员权限，用快捷方式替代）
 */
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const ROOT = 'F:\\2026\\24xs';
const JS_SCRIPT = path.join(ROOT, 'scripts\\hidden\\agent\\run-distributor-hidden.js');
const LOG_FILE = path.join(ROOT, 'autoops', 'hidden', 'distributor_task.log');

console.log('=== 内容分发器设置 ===\n');

// 1. 确保目录存在
const logDir = path.dirname(LOG_FILE);
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
  console.log(`✅ 创建日志目录: ${logDir}`);
}

// 2. 创建启动器批处理文件
const batPath = path.join(ROOT, 'scripts\\hidden\\agent\\start-distributor.bat');
const batContent = `@echo off
cd /d "${ROOT}"
node "${JS_SCRIPT}"
`;
fs.writeFileSync(batPath, batContent, 'utf-8');
console.log(`✅ 创建启动脚本: ${batPath}`);

// 3. 创建桌面快捷方式（双击运行）
const desktop = path.join(process.env.USERPROFILE || '', 'Desktop');
const shortcutPath = path.join(desktop, '24xs 内容分发器.lnk');
const ws = require('child_process').spawnSync('powershell', [
  '-Command',
  `$WshShell = New-Object -ComObject WScript.Shell;` +
  `$Shortcut = $WshShell.CreateShortcut("${shortcutPath.replace(/\\/g, '\\\\')}");` +
  `$Shortcut.TargetPath = "node.exe";` +
  `$Shortcut.Arguments = "${JS_SCRIPT.replace(/\\/g, '\\\\')}";` +
  `$Shortcut.WorkingDirectory = "${ROOT}";` +
  `$Shortcut.Description = "24xs 内容分发器";` +
  `$Shortcut.Save();`
], { encoding: 'utf-8', timeout: 15000 });

if (ws.status === 0) {
  console.log(`✅ 桌面快捷方式: ${shortcutPath}`);
} else {
  console.log('⚠️  快捷方式创建失败（可手动创建）');
}

// 4. 测试运行
console.log('\n【测试运行】');
const child = spawn('node', [JS_SCRIPT], {
  cwd: ROOT,
  stdio: 'inherit',
  detached: true,
});
child.unref();
console.log(`✅ 已后台启动 PID=${child.pid}`);

// 5. 等待几秒检查日志
setTimeout(() => {
  if (fs.existsSync(LOG_FILE)) {
    const content = fs.readFileSync(LOG_FILE, 'utf-8');
    console.log('\n【日志】');
    console.log(content.slice(-500));
  } else {
    console.log('\n日志文件尚未生成...');
  }
}, 3000);