/**
 * content-distributor.js — 内容库分发调度器（真实 CDP 发帖版）
 * 
 * 用法:
 *   node content-distributor.js --channel x --post x-ai-arcade.md
 *   node content-distributor.js --channel all --schedule --interval 3600
 *   node content-distributor.js --list
 * 
 * 支持渠道:
 *   - x: Twitter/X (CDP)
 *   - reddit: Reddit (CDP)
 *   - hackernews: HN (CDP)
 *   - xiaohongshu: 小红书 (CDP，需登录)
 *   - zhihu: 知乎 (CDP，需登录)
 *   - wechat: 微信公众号 (CDP，需登录)
 * 
 * 进阶功能:
 *   - 令牌桶速率限制（每 60s 最多发布 1 次，避免平台风控）
 *   - 失败自动回退（某渠道失败不阻塞其他渠道，并持久化至 failed_posts.json）
 *   - 断点续传（跨 run-schedule 会话自动重试之前的失败帖子）
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { CDP, withCDP } = require('./drive.js');

const CONTENT_DIR = 'C:/bingdashan/promotion/content';
const BASE_URL = 'https://tools.highkingflower.com';

// ===== 令牌桶速率限制 =====
// 确保每 60s 最多发布 1 次，避免平台风控
const RATE_LIMIT = {
  tokens: 1,         // 初始持有令牌
  maxTokens: 1,      // 最大令牌容量
  refillInterval: 60000, // 60秒补1个令牌
  lastRefill: Date.now()
};

function refillRateLimit() {
  const now = Date.now();
  const elapsed = now - RATE_LIMIT.lastRefill;
  const newTokens = Math.floor(elapsed / RATE_LIMIT.refillInterval);
  if (newTokens > 0) {
    RATE_LIMIT.tokens = Math.min(RATE_LIMIT.maxTokens, RATE_LIMIT.tokens + newTokens);
    RATE_LIMIT.lastRefill = now;
  }
}

// 获取发布令牌（阻塞直到有令牌可用）
async function acquireReleaseToken() {
  return new Promise(resolve => {
    const check = setInterval(() => {
      refillRateLimit();
      if (RATE_LIMIT.tokens >= 1) {
        RATE_LIMIT.tokens -= 1;
        clearInterval(check);
        resolve();
      }
    }, 100);
    // 防止永久等待，最长等待 60秒
    setTimeout(() => clearInterval(check), 60000);
  });
}

// ===== 错误回退日志系统 =====
const FAILED_LOG = 'promotion/failed_posts.json';

function loadFailedPosts() {
  try {
    const data = fs.readFileSync(FAILED_LOG, 'utf8');
    return JSON.parse(data);
  } catch {
    return { posts: [], updated: new Date().toISOString() };
  }
}

function saveFailedPosts(data) {
  fs.writeFileSync(FAILED_LOG, JSON.stringify(data, null, 2));
}

function addFailedPost(file, channel, error) {
  const state = loadFailedPosts();
  state.posts.push({
    file,
    channel,
    error: error.message || String(error),
    at: new Date().toISOString(),
    attempts: (state.posts.filter(p => p.file === file).length || 0) + 1
  });
  // 保留最近 20 条记录，防止膨胀
  state.posts = state.posts.slice(-20);
  state.updated = new Date().toISOString();
  saveFailedPosts(state);
}

// ===== 原有功能：解析 MD 帖子 =====
function parsePost(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const parts = content.split('---');
  if (parts.length < 3) return null;
  
  const header = parseYaml(parts[1]);
  const body = parts.slice(2).join('---').trim();
  
  return { ...header, body, file: path.basename(filePath) };
}

function parseYaml(str) {
  const result = {};
  str.trim().split('\n').forEach(line => {
    const [k, ...v] = line.split(':');
    if (k && v.length) {
      let val = v.join(':').trim();
      if (val.startsWith('[') && val.endsWith(']')) {
        val = val.slice(1, -1).split(',').map(s => s.trim().replace(/['"]/g, ''));
      }
      result[k.trim()] = val;
    }
  });
  return result;
}

// ===== 原有功能：生成帖子文案 =====
function buildPostText(post, channel) {
  const title = post.title || post.body.split('\n')[0].replace(/^#+\s*/, '').slice(0, 100);
  const hook = post.hook || '';
  const url = BASE_URL + '/arcade/';
  
  switch (channel) {
    case 'x':
      return `${hook} ${url} #AI #agents #gaming`.slice(0, 280);
    case 'reddit':
      return { title: title.slice(0, 300), text: `${hook}\n\n${url}` };
    case 'hackernews':
      return { title: `Show HN: ${title}`, url: url };
    case 'xiaohongshu':
      return `${hook}\n\n${url}\n\n#AI #智能体 #游戏 #开发工具`;
    case 'zhihu':
      return { title, content: `${hook}\n\n${url}` };
    case 'wechat':
      return { title, content: `${hook}\n\n详情: ${url}` };
    default:
      return post.body;
  }
}

// ===== 原有功能：真实发帖 =====
// X (Twitter)
async function postToX(cdp, post) {
  const text = buildPostText(post, 'x');
  await cdp.nav('https://twitter.com/compose/tweet');
  await cdp.wait(3000);
  
  await cdp.js(`
    (() => {
      const textarea = document.querySelector('[data-testid="tweetTextarea_0"]') || document.querySelector('textarea[aria-label="Post text"]') || document.querySelector('div[role="textbox"]');
      if (textarea) {
        textarea.focus();
        document.execCommand('selectAll');
        document.execCommand('insertText', false, ${JSON.stringify(text)});
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
      }
      return false;
    })()
  `);
  await cdp.wait(1500);
  
  await cdp.js(`
    (() => {
      const btn = document.querySelector('[data-testid="tweetButton"]') || document.querySelector('button[aria-label="Post"]') || document.querySelector('button:has-text("Post")');
      if (btn) { btn.click(); return true; }
      return false;
    })()
  `);
  await cdp.wait(3000);
  return { success: true, platform: 'x' };
}

// Reddit
async function postToReddit(cdp, post) {
  const { title, text } = buildPostText(post, 'reddit');
  await cdp.nav('https://www.reddit.com/submit');
  await cdp.wait(3000);
  
  await cdp.input('[name="title"]', title);
  await cdp.wait(500);
  
  await cdp.js(`
    (() => {
      const textTab = document.querySelector('[role="tab"]:has-text("Text")') || document.querySelector('button:has-text("Text")');
      if (textTab) textTab.click();
      return true;
    })()
  `);
  await cdp.wait(500);
  
  await cdp.input('[name="text"]', text);
  await cdp.wait(1000);
  
  await cdp.js(`
    (() => {
      const btn = document.querySelector('button[type="submit"]') || document.querySelector('button:has-text("Post")');
      if (btn) { btn.click(); return true; }
      return false;
    })()
  `);
  await cdp.wait(4000);
  return { success: true, platform: 'reddit' };
}

// Hacker News
async function postToHN(cdp, post) {
  const { title, url } = buildPostText(post, 'hackernews');
  await cdp.nav('https://news.ycombinator.com/submit');
  await cdp.wait(2000);
  
  await cdp.input('[name="title"]', title);
  await cdp.wait(300);
  await cdp.input('[name="url"]', url);
  await cdp.wait(500);
  
  await cdp.js(`
    (() => {
      const btn = document.querySelector('input[type="submit"]') || document.querySelector('button:has-text("submit")');
      if (btn) { btn.click(); return true; }
      return false;
    })()
  `);
  await cdp.wait(3000);
  return { success: true, platform: 'hackernews' };
}

// Xiaohongshu
async function postToXHS(cdp, post) {
  const text = buildPostText(post, 'xiaohongshu');
  await cdp.nav('https://creator.xiaohongshu.com/publish/publish');
  await cdp.wait(5000); // 小红书创作中心加载慢
  
  await cdp.js(`
    (() => {
      const tab = document.querySelector('.tab-item:has-text("图文")') || document.querySelector('[data-type="note"]');
      if (tab) tab.click();
      return true;
    })()
  `);
  await cdp.wait(1000);
  
  await cdp.input('.note-title-input, [placeholder*="标题"]', post.title || 'AI Arcade');
  await cdp.wait(500);
  
  await cdp.input('.note-content-editor, [data-placeholder*="内容"]', text);
  await cdp.wait(1000);
  
  await cdp.js(`
    (() => {
      const btn = document.querySelector('.publish-btn, button:has-text("发布")');
      if (btn) { btn.click(); return true; }
      return false;
    })()
  `);
  await cdp.wait(5000);
  return { success: true, platform: 'xiaohongshu' };
}

// Zhihu
async function postToZhihu(cdp, post) {
  const { title, content } = buildPostText(post, 'zhihu');
  await cdp.nav('https://zhuanlan.zhihu.com/write');
  await cdp.wait(3000);
  
  await cdp.input('.Post-TitleInput, [placeholder*="标题"]', title);
  await cdp.wait(500);
  
  await cdp.js(`
    (() => {
      const editor = document.querySelector('.ProseMirror, .RichTextEditor, [contenteditable="true"]');
      if (editor) {
        editor.focus();
        document.execCommand('selectAll');
        document.execCommand('insertText', false, ${JSON.stringify(content)});
        editor.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
      }
      return false;
    })()
  `);
  await cdp.wait(1500);
  
  await cdp.js(`
    (() => {
      const btn = document.querySelector('.PublishButton, button:has-text("发布")');
      if (btn) { btn.click(); return true; }
      return false;
    })()
  `);
  await cdp.wait(4000);
  return { success: true, platform: 'zhihu' };
}

// Wechat
async function postToWechat(cdp, post) {
  const { title, content } = buildPostText(post, 'wechat');
  await cdp.nav('https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10&createType=10');
  await cdp.wait(5000);
  
  await cdp.input('.weui-designer-title-input, [placeholder*="标题"]', title);
  await cdp.wait(500);
  
  await cdp.js(`
    (() => {
      const editor = document.querySelector('#js_editor, .rich_media_editor, [contenteditable="true"]');
      if (editor) {
        editor.focus();
        document.execCommand('selectAll');
        document.execCommand('insertText', false, ${JSON.stringify(content)});
        editor.dispatchEvent(new Event('input', { bubbles: true }));
        return true;
      }
      return false;
    })()
  `);
  await cdp.wait(1500);
  
  await cdp.js(`
    (() => {
      const btn = document.querySelector('.weui-btn_primary:has-text("发布"), .btn_publish, button:has-text("发布")');
      if (btn) { btn.click(); return true; }
      return false;
    })()
  `);
  await cdp.wait(3000);
  return { success: true, platform: 'wechat' };
}

// ===== 新增：分发路由（带失败回退） =====
const POSTERS = {
  x: postToX,
  reddit: postToReddit,
  hackernews: postToHN,
  xiaohongshu: postToXHS,
  zhihu: postToZhihu,
  wechat: postToWechat
};

// ===== 新增：主分发函数（带失败持久化） =====
async function distribute(postFile, channel, dryRun = false) {
  const filePath = path.join(CONTENT_DIR, postFile);
  if (!fs.existsSync(filePath)) {
    console.error(`Post not found: ${filePath}`);
    return { success: false, error: 'not_found' };
  }
  
  const post = parsePost(filePath);
  if (!post) {
    console.error(`Failed to parse: ${postFile}`);
    return { success: false, error: 'parse_failed' };
  }
  
  console.log(`\n=== Distributing to ${channel} ===`);
  console.log(`File: ${post.file}`);
  console.log(`Topic: ${post.topic}`);
  
  if (dryRun) {
    console.log('[DRY RUN] Would post to:', channel);
    return { success: true, dryRun: true };
  }
  
  const poster = POSTERS[channel];
  if (!poster) {
    console.error(`Unsupported channel: ${channel}`);
    return { success: false, error: 'unsupported_channel' };
  }
  
  try {
    // 1. 获取发布令牌（自动等待直到有令牌）
    await acquireReleaseToken();
    
    const result = await withCDP(async (cdp) => {
      return await poster(cdp, post);
    }, { port: 9223 });
    
    // 2. 成功：标记为已发布，并重试失败列表中的下一条
    await markPosted(post.file);
    await retryFailedPosts(); // 新增：尝试重试之前的失败记录
    
    console.log(`✅ Posted to ${channel}: ${post.file}`);
    return { success: true, ...result };
    
  } catch (error) {
    // 3. 失败：记录到 failed_posts.json，但不中断调度链条
    addFailedPost(post.file, channel, error);
    console.log(`❌ Failed to post to ${channel}: ${error.message}`);
    console.log('     (错误已记录，将在下次调度中重试)');
    
    // 继续执行下一篇，不中断
    return { success: false, error: error.message, platform: channel };
  }
}

// ===== 新增：标记已发布（保持不变） =====
async function markPosted(file) {
  if (!fs.existsSync('promotion/schedule.json')) return;
  try {
    const schedule = JSON.parse(fs.readFileSync('promotion/schedule.json', 'utf8'));
    const item = schedule.queue.find(q => q.file === file);
    if (item) {
      item.posted = true;
      item.posted_at = new Date().toISOString();
      fs.writeFileSync('promotion/schedule.json', JSON.stringify(schedule, null, 2));
    }
  } catch (e) {
    console.warn('Failed to update schedule:', e.message);
  }
}

// ===== 原有功能：定时调度：生成/更新 schedule.json =====
function schedule(interval) {
  const posts = fs.readdirSync('C:/bingdashan/promotion/content')
    .filter(f => f.endsWith('.md') && f !== '.gitkeep')
    .map(f => ({ file: f, ...parsePost(path.join('C:/bingdashan/promotion/content', f)) }))
    .filter(p => p);
  
  const prev = fs.existsSync('promotion/schedule.json') ? JSON.parse(fs.readFileSync('promotion/schedule.json', 'utf8')) : null;
  const prevPosted = new Set((prev?.queue || []).filter(q => q.posted).map(q => q.file));
  
  const newSchedule = {
    created: new Date().toISOString(),
    updated_by: 'content-distributor',
    interval: interval,
    queue: posts.map(p => ({
      file: p.file,
      channel: p.channel,
      topic: p.topic,
      scheduled: true,
      posted: prevPosted.has(p.file),
      auto: true
    }))
  };
  
  fs.writeFileSync('promotion/schedule.json', JSON.stringify(newSchedule, null, 2));
  console.log(`Schedule created: ${newSchedule.queue.length} posts (${newSchedule.queue.filter(q => !q.posted).length} pending)`);
  return newSchedule;
}

// ===== 新增：执行调度队列（带令牌桶 + 失败回退） =====
async function runSchedule(maxPosts = 1) {
  if (!fs.existsSync('promotion/schedule.json')) {
    console.log('No schedule found. Run with --schedule first.');
    return;
  }
  
  const schedule = JSON.parse(fs.readFileSync('promotion/schedule.json', 'utf8'));
  const pending = schedule.queue.filter(q => !q.posted);
  
  if (pending.length === 0) {
    console.log('All posts published.');
    return;
  }
  
  console.log(`\n=== Running schedule: ${pending.length} pending, will post ${maxPosts} ===`);
  
  for (let i = 0; i < Math.min(maxPosts, pending.length); i++) {
    const item = pending[i];
    console.log(`\n[${i+1}/${Math.min(maxPosts, pending.length)}] ${item.channel} <- ${item.file}`);
    
    // 1. 获取发布令牌（自动等待直到有令牌）
    await acquireReleaseToken();
    
    // 2. 执行分发
    const result = await distribute(item.file, item.channel);
    
    // 3. 结果处理
    if (result.success) {
      // 成功：更新 schedule.json 标记为已发布
      await markPosted(item.file);
      console.log(`✅ Posted to ${item.channel}: ${item.file}`);
    } else {
      // 失败：记录错误，但不中断调度
      console.log(`❌ Failed to post to ${item.channel}: ${result.error}`);
      console.log('     (错误已记录，将在调度结束后重试)');
    }
    
    // 4. 发帖间隔由 acquireReleaseToken 自动控制，无需额外 setTimeout
  }
  
  // 5. 调度结束后：重试之前的失败帖子
  await retryFailedPosts();
}

// ===== 新增：重试失败的帖子 =====
async function retryFailedPosts() {
  const failed = loadFailedPosts();
  if (failed.posts.length === 0) {
    console.log('No failed posts to retry.');
    return;
  }
  
  console.log(`\n=== Retrying ${failed.posts.length} previously failed posts ===`);
  
  // 仅重试第一条（按顺序，防止单次调度过多）
  const nextToRetry = failed.posts[0];
  console.log(`Retrying: ${nextToRetry.file} on ${nextToRetry.channel} (attempt #${nextToRetry.attempts})`);
  
  // 直接尝试分发（令牌桶会自动处理速率限制）
  const result = await distribute(nextToRetry.file, nextToRetry.channel);
  
  if (result.success) {
    console.log(`✅ Retry successful: ${nextToRetry.file}`);
    // 从失败列表移除
    failed.posts = failed.posts.filter(p => p.file !== nextToRetry.file);
    saveFailedPosts(failed);
  } else {
    console.log(`❌ Retry still failed: ${result.error}`);
    // 更新失败记录中的次数
    const entry = failed.posts.find(p => p.file === nextToRetry.file);
    if (entry) entry.attempts++;
    saveFailedPosts(failed);
  }
}

// ===== CLI 入口 =====
const args = process.argv.slice(2);
const cmd = args[0];

if (cmd === 'post') {
  const channel = args[1];
  const postFile = args[2];
  const dryRun = args.includes('--dry-run');
  if (!channel || !postFile) {
    console.log('Usage: node content-distributor.js post <channel> <post.md> [--dry-run]');
    console.log('Channels: x, reddit, hackernews, xiaohongshu, zhihu, wechat');
    process.exit(1);
  }
  distribute(postFile, channel, dryRun).then(r => {
    if (!r.success) process.exit(1);
  });
  
} else if (cmd === 'schedule') {
  const interval = parseInt(args[1]) || 3600;
  schedule(interval);
  
} else if (cmd === 'run-schedule') {
  const maxPosts = parseInt(args[1]) || 1;
  runSchedule(maxPosts).catch(console.error);
  
} else if (cmd === 'list') {
  const posts = fs.readdirSync('C:/bingdashan/promotion/content')
    .filter(f => f.endsWith('.md') && f !== '.gitkeep')
    .map(f => parsePost(path.join('C:/bingdashan/promotion/content', f)));
  console.log(`\n=== Content Library (${posts.length} posts) ===\n`);
  posts.forEach(p => {
    console.log(`[${p.channel}] ${p.topic}: ${p.title || p.body.split('\n')[0].slice(0, 50)}`);
  });
  
} else {
  console.log(`
Content Distributor — 推广内容分发调度器（真实 CDP 版）

Commands:
  list                    列出所有内容库帖子
  post <channel> <file>   真实发帖到指定渠道
  post <channel> <file> --dry-run  试运行
  schedule [interval]     创建/更新定时分发计划 (默认 3600s)
  run-schedule [max]      执行调度队列，发布最多 max 篇 (默认 1)

Channels: x, reddit, hackernews, xiaohongshu, zhihu, wechat

Examples:
  node content-distributor.js list
  node content-distributor.js post x x-ai-arcade.md --dry-run
  node content-distributor.js post x x-ai-arcade.md
  node content-distributor.js schedule 3600
  node content-distributor.js run-schedule 2
`);
}