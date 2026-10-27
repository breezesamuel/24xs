#!/usr/bin/env node
/**
 * 更新 24xs 计划任务：将 VBScript 替换为 Node.js 脚本
 */
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const ROOT = 'F:\\2026\\24xs';
const OLD_VBS = path.join(ROOT, 'scripts\\hidden\\agent\\run-distributor-hidden.vbs');
const NEW_JS = path.join(ROOT, 'scripts\\hidden\\agent\\run-distributor-hidden.js');

console.log('=== 更新 24xs 计划任务 ===\n');

// 1. 查现有计划任务
console.log('【现有计划任务】');
try {
  const out = execSync('schtasks /query /fo LIST /v', { encoding: 'utf-8', timeout: 15000 });
  const lines = out.split('========================================');
  for (const block of lines) {
    if (block.toLowerCase().includes('distributor') || block.toLowerCase().includes('autoops')) {
      console.log(block.slice(0, 400));
      console.log('---');
    }
  }
} catch (e) {
  console.log('查任务失败:', e.message.slice(0, 200));
}

// 2. 删旧任务（如果存在）
console.log('\n【删除旧任务】');
try {
  execSync('schtasks /delete /tn "\\AutoOps\\Distributor" /f', { encoding: 'utf-8', timeout: 15000 });
  console.log('  ✅ 已删除 \\AutoOps\\Distributor');
} catch (e) {
  console.log('  任务不存在或删除失败:', e.message.slice(0, 100));
}

// 3. 创建新任务（用 Node.js 脚本）
console.log('\n【创建新任务】');
const taskXml = `<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>24xs 内容分发调度器（Node.js 版）</Description>
    <Author>bingdashan</Author>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <Repetition>
        <Interval>PT30M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
      <StartBoundary>2026-10-25T12:00:00</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>node</Command>
      <Arguments>"${NEW_JS}"</Arguments>
      <WorkingDirectory>${ROOT}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>`;

const taskFile = path.join(ROOT, 'autoops', 'distributor_task.xml');
fs.mkdirSync(path.dirname(taskFile), { recursive: true });
fs.writeFileSync(taskFile, taskXml, 'utf-8');

try {
  execSync(`schtasks /create /tn "\\AutoOps\\Distributor" /xml "${taskFile}" /f`, { encoding: 'utf-8', timeout: 15000 });
  console.log('  ✅ 计划任务已创建: \\AutoOps\\Distributor');
} catch (e) {
  console.log('  ❌ 创建任务失败:', e.message.slice(0, 200));
}

// 4. 验证
console.log('\n【验证】');
try {
  const out = execSync('schtasks /query /tn "\\AutoOps\\Distributor" /fo LIST /v', { encoding: 'utf-8', timeout: 15000 });
  const lines = out.split('\n');
  for (const line of lines) {
    if (line.includes('Last Run') || line.includes('Next Run') || line.includes('Status')) {
      console.log('  ' + line.trim());
    }
  }
} catch (e) {
  console.log('  验证失败:', e.message.slice(0, 100));
}

// 5. 备份并删除旧 VBS
console.log('\n【清理旧文件】');
if (fs.existsSync(OLD_VBS)) {
  const backup = OLD_VBS + '.backup';
  fs.copyFileSync(OLD_VBS, backup);
  console.log(`  ✅ 已备份: ${backup}`);
  // 不删除，保留备份
}
console.log(`  ℹ️  旧 VBS 保留为备份: ${OLD_VBS}.backup`);

console.log('\n完成！计划任务每 30 分钟自动运行 Node.js 分发脚本');
