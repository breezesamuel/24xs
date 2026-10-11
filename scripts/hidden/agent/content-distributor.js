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
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { CDP, withCDP } = require('./drive.js');

const CONTENT_DIR = 'C:/bingdashan/promotion/content';
const SCHEDULE_FILE = 'C:/bingdashan/promotion/schedule.json';
const BASE_URL = 'https://tools.highkingflower.com';

// 解析 MD 帖子
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

// 生成帖子文案（根据渠道定制）
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

// 真实发帖：X (Twitter)
async function postToX(cdp, post) {
  const text = buildPostText(post, 'x');
  await cdp.nav('https://twitter.com/compose/tweet');
  await cdp.wait(3000);
  
  // 等待编辑器出现
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
  
  // 点击发布按钮
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

// 真实发帖：Reddit
async function postToReddit(cdp, post) {
  const { title, text } = buildPostText(post, 'reddit');
  await cdp.nav('https://www.reddit.com/submit');
  await cdp.wait(3000);
  
  // 填写标题
  await cdp.input('[name="title"]', title);
  await cdp.wait(500);
  
  // 切换到文本模式（如果需要）
  await cdp.js(`
    (() => {
      const textTab = document.querySelector('[role="tab"]:has-text("Text")') || document.querySelector('button:has-text("Text")');
      if (textTab) textTab.click();
      return true;
    })()
  `);
  await cdp.wait(500);
  
  // 填写正文
  await cdp.input('[name="text"]', text);
  await cdp.wait(1000);
  
  // 选择 subreddit（可选，默认使用用户主页）
  // 点击发布
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

// 真实发帖：Hacker News
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

// 真实发帖：小红书
async function postToXHS(cdp, post) {
  const text = buildPostText(post, 'xiaohongshu');
  await cdp.nav('https://creator.xiaohongshu.com/publish/publish');
  await cdp.wait(5000); // 小红书创作中心加载慢
  
  // 选择图文模式
  await cdp.js(`
    (() => {
      const tab = document.querySelector('.tab-item:has-text("图文")') || document.querySelector('[data-type="note"]');
      if (tab) tab.click();
      return true;
    })()
  `);
  await cdp.wait(1000);
  
  // 填写标题
  await cdp.input('.note-title-input, [placeholder*="标题"]', post.title || 'AI Arcade');
  await cdp.wait(500);
  
  // 填写正文
  await cdp.input('.note-content-editor, [data-placeholder*="内容"]', text);
  await cdp.wait(1000);
  
  // 发布
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

// 真实发帖：知乎
async function postToZhihu(cdp, post) {
  const { title, content } = buildPostText(post, 'zhihu');
  await cdp.nav('https://zhuanlan.zhihu.com/write');
  await cdp.wait(3000);
  
  await cdp.input('.Post-TitleInput, [placeholder*="标题"]', title);
  await cdp.wait(500);
  
  // 知乎编辑器通常是 contenteditable div
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

// 真实发帖：微信公众号
async function postToWechat(cdp, post) {
  const { title, content } = buildPostText(post, 'wechat');
  await cdp.nav('https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10&createType=10');
  await cdp.wait(5000);
  
  await cdp.input('.weui-designer-title-input, [placeholder*="标题"]', title);
  await cdp.wait(500);
  
  // 微信编辑器
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
  
  // 保存草稿/发布
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

// 分发路由
const POSTERS = {
  x: postToX,
  reddit: postToReddit,
  hackernews: postToHN,
  xiaohongshu: postToXHS,
  zhihu: postToZhihu,
  wechat: postToWechat
};

// 主分发函数（真实执行）
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
    const result = await withCDP(async (cdp) => {
      return await poster(cdp, post);
    }, { port: 9223 });
    
    // 更新 schedule.json 标记为已发布
    await markPosted(post.file);
    
    console.log(`✅ Posted to ${channel}: ${post.file}`);
    return { success: true, ...result };
    
  } catch (error) {
    console.error(`❌ Failed to post to ${channel}:`, error.message);
    return { success: false, error: error.message };
  }
}

// 标记已发布
async function markPosted(file) {
  if (!fs.existsSync(SCHEDULE_FILE)) return;
  try {
    const schedule = JSON.parse(fs.readFileSync(SCHEDULE_FILE, 'utf8'));
    const item = schedule.queue.find(q => q.file === file);
    if (item) {
      item.posted = true;
      item.posted_at = new Date().toISOString();
      fs.writeFileSync(SCHEDULE_FILE, JSON.stringify(schedule, null, 2));
    }
  } catch (e) {
    console.warn('Failed to update schedule:', e.message);
  }
}

// 定时调度：生成/更新 schedule.json
function schedule(interval) {
  const posts = fs.readdirSync(CONTENT_DIR)
    .filter(f => f.endsWith('.md') && f !== '.gitkeep')
    .map(f => ({ file: f, ...parsePost(path.join(CONTENT_DIR, f)) }))
    .filter(p => p);
  
  const prev = fs.existsSync(SCHEDULE_FILE) ? JSON.parse(fs.readFileSync(SCHEDULE_FILE, 'utf8')) : null;
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
  
  fs.writeFileSync(SCHEDULE_FILE, JSON.stringify(newSchedule, null, 2));
  console.log(`Schedule created: ${newSchedule.queue.length} posts (${newSchedule.queue.filter(q => !q.posted).length} pending)`);
  return newSchedule;
}

// 执行调度队列（按顺序发布未发布的）
async function runSchedule(maxPosts = 1) {
  if (!fs.existsSync(SCHEDULE_FILE)) {
    console.log('No schedule found. Run with --schedule first.');
    return;
  }
  
  const schedule = JSON.parse(fs.readFileSync(SCHEDULE_FILE, 'utf8'));
  const pending = schedule.queue.filter(q => !q.posted);
  
  if (pending.length === 0) {
    console.log('All posts published.');
    return;
  }
  
  console.log(`\n=== Running schedule: ${pending.length} pending, will post ${maxPosts} ===`);
  
  for (let i = 0; i < Math.min(maxPosts, pending.length); i++) {
    const item = pending[i];
    console.log(`\n[${i+1}/${Math.min(maxPosts, pending.length)}] ${item.channel} <- ${item.file}`);
    const result = await distribute(item.file, item.channel);
    
    if (!result.success && !result.dryRun) {
      console.log(`Stopping schedule due to failure: ${result.error}`);
      break;
    }
    
    // 发帖间隔，避免风控
    if (i < Math.min(maxPosts, pending.length) - 1) {
      console.log('Waiting 60s before next post...');
      await new Promise(r => setTimeout(r, 60000));
    }
  }
}

// CLI 入口
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
  const posts = fs.readdirSync(CONTENT_DIR)
    .filter(f => f.endsWith('.md') && f !== '.gitkeep')
    .map(f => parsePost(path.join(CONTENT_DIR, f)));
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