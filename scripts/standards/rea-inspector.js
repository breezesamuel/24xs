#!/usr/bin/env node
/**
 * rea-inspector.mjs — REA（Reverse Engineer Anything）驱动的闭环：
 * 1. 分析 failed_posts.json 中的失败样本
 * 2. 按渠道/错误类型分组，给出 root_cause + fix_suggestion（纯文字，用户手动 copy-paste 写入）
 * 3. （可选）自动在 content-distributor.js 对应渠道分支写入 `// REA Fix: ...` 评论行
 *
 * 用法：
 *   node rea-inspector.mjs                    # 仅分析输出
 *   node rea-inspector.mjs --write           # 分析并自动写入 // REA Fix: 评论行
 */
const fs = require('fs');
const path = require('path');

const REPO_ROOT = process.cwd();
const FAILED_FILE = path.join(REPO_ROOT, 'promotion', 'failed_posts.json');
const CD_FILE = path.join(REPO_ROOT, 'scripts', 'hidden', 'agent', 'content-distributor.js');
const BACKUP_FILE = CD_FILE + '.backup.' + new Date().toISOString().slice(0,10);

const FAILED = JSON.parse(fs.readFileSync(FAILED_FILE, 'utf8'));

// ── 1. 分类统计 ──
const stats = {};
for (const p of FAILED.posts) {
  const key = `${p.channel}:${p.error}`;
  if (!stats[key]) stats[key] = { count: 0, samples: [] };
  stats[key].count++;
  stats[key].samples.push(p.file);
}

// 按渠道分组
const byChannel = {};
for (const p of FAILED.posts) {
  if (!byChannel[p.channel]) byChannel[p.channel] = [];
  byChannel[p.channel].push(p);
}

// ── 2. 为每种错误类型生成诊断 + 修复建议（纯文字，用户 copy-paste）──

const fixTemplates = {

  // --- 模式 A：_getTargets is not a function ---
  'x:this._getTargets is not a function': {
    root_cause:
      'CDP target方法 mismatch。_getTargets可能指代 drive.js 内部方法，但当前 connected target可能是 worker/service worker/other，或连接的页面已导航 Away。',
    fix_suggestion:
      '// REA Fix: _getTargets 不存在时兜底\n// 在 drive.js connect() 后增加 safeGetTargets(cdp) 动，避免 _getTargets 因 target 类型错误而报错。',
  },

  // --- 模式 B：Element not found: [name="title"] ---
  'hackernews:Element not found: [name="title"]': {
    root_cause:
      'HN submit 页未登录（重定向到 /login），或页面未完全加载。[name="title"]仅在已登录后的 submit 表单中存在。',
    fix_suggestion:
      '// REA Fix: HN 登录态检测 + 备选 selector\n// 在分发前探测 HN 登录态（检测 [name="acct"] 是否存在），未登录则跳过或引导登录页。',
  },

  // --- 模式 C：Uncaught (小红书 JS 错误) ---
  'xiaohongshu:Uncaught': {
    root_cause:
      '小红书 CSP/动态 SPA 环境下，JS 注入/元素操作时的未捕获异常。可能是内容editable/textarea 在特定 DOM结构下不可写。',
    fix_suggestion:
      '// REA Fix: 小红书 just-break-early + try.catch兜底\n// 发帖前探测编辑器就绪状态（querySelector input/textarea/[contenteditable]), 未就绪则跳过本次发帖，并 enter try/catch 避免 Uncaught 中断主流程。',
  },

  // --- 默认兜底：未分类错误 ---
  default: {
    root_cause: '未在预设模式中匹配的错误，需人工复检',
    fix_suggestion:
      '// REA Fix: 人工复检\n// 1. 运行 doctor 探测网络/登录态 2. 手动检查 failed_posts.json 对应条目日志 3. 苄仍无法定位，可将本错误记录加入预设模式',
  },
};

// ── 3. 输出分析报告 ──
function analyze() {
  const report = {
    timestamp: new Date().toISOString(),
    total_failures: FAILED.posts.length,
    channels: Object.keys(byChannel),
    breakdown: {},
    fixes: {},
  };

  for (const [key, info] of Object.entries(stats)) {
    const [channel, error] = key.split(':');
    report.breakdown[channel] = report.breakdown[channel] || {};
    report.breakdown[channel][error] = {
      count: info.count,
      samples: info.samples,
      root_cause: fixTemplates[key] ? fixTemplates[key].root_cause : fixTemplates.default.root_cause,
      fix_suggestion: fixTemplates[key] ? fixTemplates[key].fix_suggestion : fixTemplates.default.fix_suggestion,
    };
    report.fixes[channel] = fixTemplates[key] ? fixTemplates[key].fix_suggestion : fixTemplates.default.fix_suggestion;
  }

  console.log('\=== REA Inspector Report ===');
  console.log(`总失败数: ${report.total_failures}\\n`);
  for (const [ch, errors] of Object.entries(report.breakdown)) {
    console.log(`渠道 ${ch}: ${Object.values(errors).map(e => `${e.count}次`).join(' + ')}`);
    for (const [err, info] of Object.entries(errors)) {
      console.log(`  错误 ${err}:`);
      console.log(`    原因: ${info.root_cause}`);
      console.log(`    建议: ${info.fix_suggestion}\\n`);
    }
  }
  console.log('=============================\\\n');
  console.log('每条渠道的 fix_suggestion 以上文本实文字，用户可直接 copy-paste 写入 content-distributor.js 的对应渠道分支。');
  console.log('若要自动写入 // REA Fix: 评论行，传入 --write 参数。');
  return report;
}

// ── 4. 自动写入 // REA Fix: 评论行 ──
function writeFixes() {
  let cdContent = fs.readFileSync(CD_FILE, 'utf8');

  // 为每个渠道在 distribute() 函数开头之后写入 // REA Fix: 评论行
  const marker = '// ===== 新增：主分发函数（带失败持久化） =====\nasync function distribute';
  if (cdContent.indexOf(marker) === -1) {
    console.log('未找到 distribute() 标记，跳过写入');
    return;
  }

  for (const [ch, fix] of Object.entries(fixTemplates)) {
    const searchStr = `// REA Fix:${ch}`;
    if (cdContent.indexOf(searchStr) === -1) {
      // 在 marker 之后插入一个评论行
      const insertLine = `// REA Fix:${ch}\\n`;
      cdContent = cdContent.replace(marker, marker + insertLine);
    }
  }

  //备份
  try {
    fs.copyFileSync(CD_FILE, BACKUP_FILE);
    console.log(`已备份原文件至: ${BACKUP_FILE}`);
  } catch (e) {
    console.log('备份失败:', e.message);
  }
  fs.writeFileSync(CD_FILE, cdContent, 'utf8');
  console.log(`已将 ${Object.keys(fixTemplates).length} 条 // REA Fix: 评论行写入 ${CD_FILE}`);
}

// ── 5. 主流程 ──
async function main() {
  const args = process.argv.slice(2);
  const doWrite = args.includes('--write');

  const report = analyze();

  if (doWrite) {
    writeFixes();
  } else {
    console.log('--- 分析模式（未写入）。传入 --write 以自动写入 // REA Fix: 评论行。');
  }
}

main().catch(e => console.error('REE Inspector error:', e.message));