/**
 * drive.js — 极简 CDP 驱动（直连 Chrome DevTools Protocol）
 * 用途：复用已登录浏览器 (:9223) 进行 X/Reddit/HN/WeChat/小红书/知乎 发帖
 * 设计：零依赖，仅用 Node 内置 net/WebSocket；无 Puppeteer/Playwright 抽象层
 * 要求：Chrome/Edge 以 --remote-debugging-port=9223 启动，且已登录目标站点
 */
'use strict';

const net = require('net');
const http = require('http');
const { WebSocket } = require('ws');

class CDP {
  constructor({ port = 9223, host = '127.0.0.1' } = {}) {
    this.host = host;
    this.port = port;
    this.ws = null;
    this.msgId = 0;
    this.pending = new Map();
    this.connected = false;
    this.targetId = null;
  }

  // 连接 CDP：获取可用 target -> 建立 WebSocket -> 启用域
  async connect() {
    const targets = await this._getTargets();
    // 优先找已打开的普通页面，其次创建新标签
    const page = targets.find(t => t.type === 'page' && !t.url.startsWith('devtools://') && !t.url.startsWith('chrome://'));
    if (page) {
      this.targetId = page.targetId;
    } else {
      const created = await this._createTarget('about:blank');
      this.targetId = created.targetId;
    }
    const wsUrl = `ws://${this.host}:${this.port}/devtools/page/${this.targetId}`;
    await this._connectWS(wsUrl);
    // 启用常用域
    await this.send('Runtime.enable');
    await this.send('Network.enable');
    await this.send('Page.enable');
    await this.send('DOM.enable');
    await this.send('Input.enable');
    this.connected = true;
    return this;
  }

  _getTargets() {
    return new Promise((resolve, reject) => {
      http.get(`http://${this.host}:${this.port}/json/list`, res => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => {
          try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
        });
      }).on('error', reject);
    });
  }

  _createTarget(url) {
    return new Promise((resolve, reject) => {
      const req = http.request({
        hostname: this.host,
        port: this.port,
        path: '/json/new?' + new URLSearchParams({ url }).toString(),
        method: 'PUT'
      }, res => {
        let data = '';
        res.on('data', c => data += c);
        res.on('end', () => {
          try { resolve(JSON.parse(data)); } catch (e) { reject(e); }
        });
      });
      req.on('error', reject);
      req.end();
    });
  }

  _connectWS(url) {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(url);
      this.ws.on('open', () => resolve());
      this.ws.on('error', reject);
      this.ws.on('message', data => {
        try {
          const msg = JSON.parse(data.toString());
          if (msg.id && this.pending.has(msg.id)) {
            const { resolve, reject } = this.pending.get(msg.id);
            this.pending.delete(msg.id);
            if (msg.error) reject(new Error(msg.error.message));
            else resolve(msg.result);
          }
          // 事件处理可在此扩展
        } catch (e) { /* ignore parse errors */ }
      });
      this.ws.on('close', () => { this.connected = false; });
    });
  }

  // 发送 CDP 命令
  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return reject(new Error('CDP not connected'));
      const id = ++this.msgId;
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
      // 超时保护
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id);
          reject(new Error(`CDP timeout: ${method}`));
        }
      }, 30000);
    });
  }

  // 导航并等待加载
  async nav(url, waitUntil = 'networkidle2', timeout = 30000) {
    await this.send('Page.navigate', { url });
    if (waitUntil === 'networkidle2') {
      await this.send('Network.setCacheDisabled', { cacheDisabled: true });
      // 简单等待：监听 loading 完成（实际可监听 Network.loadingFinished）
      await this.wait(2000);
    }
    return this;
  }

  // 等待毫秒
  wait(ms) {
    return new Promise(r => setTimeout(r, ms));
  }

  // 在页面上下文执行 JS
  async js(code, awaitPromise = true) {
    const res = await this.send('Runtime.evaluate', {
      expression: code,
      awaitPromise,
      returnByValue: true,
      userGesture: true
    });
    if (res.exceptionDetails) throw new Error(res.exceptionDetails.text);
    return res.result?.value;
  }

  // 点击选择器
  async click(selector, options = {}) {
    // 先获取元素位置
    const box = await this.js(`
      (() => {
        const el = document.querySelector(${JSON.stringify(selector)});
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: r.left + r.width/2, y: r.top + r.height/2 };
      })()
    `);
    if (!box) throw new Error(`Element not found: ${selector}`);
    await this.send('Input.dispatchMouseEvent', {
      type: 'mousePressed', x: box.x, y: box.y, button: 'left', clickCount: 1, ...options
    });
    await this.wait(100);
    await this.send('Input.dispatchMouseEvent', {
      type: 'mouseReleased', x: box.x, y: box.y, button: 'left', clickCount: 1, ...options
    });
    return this;
  }

  // 输入文本
  async input(selector, text, options = {}) {
    await this.click(selector);
    await this.wait(100);
    // 全选删除
    await this.send('Input.dispatchKeyEvent', { type: 'keyDown', modifiers: 2, key: 'a', code: 'KeyA' }); // Ctrl+A
    await this.send('Input.dispatchKeyEvent', { type: 'keyUp', modifiers: 2, key: 'a', code: 'KeyA' });
    await this.wait(50);
    // 逐字符输入（绕过某些输入法拦截）
    for (const ch of text) {
      await this.send('Input.insertText', { text: ch });
      await this.wait(options.delay || 30);
    }
    return this;
  }

  // 滚动
  async scroll(x = 0, y = 500) {
    await this.js(`window.scrollBy(${x}, ${y})`);
    return this;
  }

  // 截图
  async screenshot({ format = 'png', quality = 80 } = {}) {
    const res = await this.send('Page.captureScreenshot', { format, quality });
    return Buffer.from(res.data, 'base64');
  }

  // 关闭
  async close() {
    if (this.ws) { this.ws.close(); this.ws = null; }
    this.connected = false;
  }
}

// 导出便捷函数：自动连接、执行、关闭
async function withCDP(fn, options) {
  const cdp = new CDP(options);
  await cdp.connect();
  try {
    return await fn(cdp);
  } finally {
    await cdp.close();
  }
}

module.exports = { CDP, withCDP };