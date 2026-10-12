/**
 * drive.js — 极简 CDP 驱动（直连 Chrome DevTools Protocol）
 * 用途：复用已登录浏览器 (:9223) 进行 X/Reddit/HN/WeChat/小红书/知乎 发帖
 * 设计：零依赖，仅用 Node 内置 net/WebSocket；无 Puppeteer/Playwright 抽象层
 * 要求：Chrome/Edge 以 --remote-debugging-port=9223 启动，且已登录目标站点
 */
'use strict';

const net = require('net');
const http = require('http');
// Use global WebSocket (Node.js 25 built-in); fallback to ws package if needed
const wsClass = typeof WebSocket !== 'undefined' ? WebSocket : require('ws');

class CDP {
  constructor({ port = 9223, host = '127.0.0.1' } = {}) {
    this.host = host;
    this.port = port;
    this.ws = null;
    this.msgId = 0;
    this.pending = new Map();
    this.connected = false;
    this.targetId = null;
    this.lastHeartbeat = 0;
    this.heartbeatInterval = null;
    this.heartbeatTimeout = null;
    this.maxHeartbeatAge = 60000;
    this.closing = false;
  }

  // === 连接 ===

  async connect() {
    const targets = await this._getTargets();

    let page = targets.find(
      t => t.type === 'page' && !t.url.startsWith('devtools://') && !t.url.startsWith('chrome://')
    );
    if (!page) {
      const created = await this._createTarget('about:blank');
      const info = await this._getTargetInfo(created.targetId);
      page = info;
    }

    this.targetId = page.targetId;
    const wsUrl = `ws://${this.host}:${this.port}/devtools/page/${this.targetId}`;
    await this._connectWS(wsUrl);

    await this.send('Runtime.enable');
    await this.send('Network.enable');
    await this.send('Page.enable');
    await this.send('DOM.enable');

    this.connected = true;
    this.lastHeartbeat = Date.now();
    this._startHeartbeat();
    return this;
  }

  // === CDP HTTP 端点（/json/list、/json/new） ===

  _httpGet(pathname, method = 'GET') {
    return new Promise((resolve, reject) => {
      const req = http.request(
        { host: this.host, port: this.port, path: pathname, method, timeout: 5000 },
        res => {
          let d = '';
          res.on('data', c => { d += c; });
          res.on('end', () => {
            let json = null;
            try { json = d ? JSON.parse(d) : null; } catch (e) {}
            resolve({ status: res.statusCode, json, text: d });
          });
        }
      );
      req.on('error', reject);
      req.on('timeout', () => req.destroy(new Error('cdp http timeout')));
      req.end();
    });
  }

  async _getTargets() {
    const r = await this._httpGet('/json/list');
    if (!Array.isArray(r.json)) return [];
    return r.json.map(t => ({ targetId: t.id, type: t.type, url: t.url, wsUrl: t.webSocketDebuggerUrl }));
  }

  async _createTarget(url) {
    // Chrome >= v111 要求 PUT /json/new?<url>
    let r = await this._httpGet('/json/new?' + encodeURIComponent(url), 'PUT');
    if (!r.json) r = await this._httpGet('/json/new?' + encodeURIComponent(url), 'GET');
    const id = r.json && (r.json.id || r.json.targetId);
    if (!id) throw new Error('CDP createTarget failed (status ' + r.status + ')');
    return { targetId: id, type: r.json.type, url: r.json.url };
  }

  async _getTargetInfo(targetId) {
    const targets = await this._getTargets();
    const t = targets.find(x => x.targetId === targetId);
    if (!t) throw new Error('CDP target not found: ' + targetId);
    return t;
  }

  async _connectWS(wsUrl) {
    await new Promise((resolve, reject) => {
      let settled = false;
      const ws = new wsClass(wsUrl);
      ws.onopen = () => { settled = true; this.ws = ws; resolve(); };
      ws.onerror = e => { if (!settled) { settled = true; reject(new Error('CDP ws error: ' + ((e && e.message) || 'unknown'))); } };
      ws.onmessage = ev => this._onMessage(ev.data);
      ws.onclose = () => { if (!this.closing && this.ws === ws) { this.ws = null; this._onWsClosed(); } };
    });
  }

  _onMessage(data) {
    let msg = null;
    try { msg = JSON.parse(typeof data === 'string' ? data : Buffer.from(data).toString('utf8')); } catch (e) { return; }
    if (msg && msg.id !== undefined && this.pending.has(msg.id)) {
      const { resolve, reject } = this.pending.get(msg.id);
      this.pending.delete(msg.id);
      if (msg.error) reject(new Error(msg.error.message || 'CDP error'));
      else resolve(msg.result);
    }
  }

  // === 心跳 ===

  _startHeartbeat() {
    clearInterval(this.heartbeatInterval);
    this.heartbeatInterval = setInterval(() => this._sendHeartbeat(), 30000);
    if (this.heartbeatInterval.unref) this.heartbeatInterval.unref();
    clearTimeout(this.heartbeatTimeout);
    this.heartbeatTimeout = setTimeout(() => this._checkHeartbeatTimeout(), 60000);
    if (this.heartbeatTimeout.unref) this.heartbeatTimeout.unref();
  }

  _sendHeartbeat() {
    if (this.closing) return;
    if (!this.ws || this.ws.readyState !== wsClass.OPEN) {
      this._requestReconnect('heartbeat send failed');
      return;
    }
    this.send('Runtime.evaluate', { expression: '1', awaitPromise: false, returnByValue: true, userGesture: true })
      .then(() => { this.lastHeartbeat = Date.now(); })
      .catch(() => { if (Date.now() - this.lastHeartbeat > this.maxHeartbeatAge) this._requestReconnect('heartbeat timeout'); });
  }

  _checkHeartbeatTimeout() {
    if (this.closing) return;
    if (this.connected && Date.now() - this.lastHeartbeat > this.maxHeartbeatAge) this._requestReconnect('stale heartbeat');
    this.heartbeatTimeout = setTimeout(() => this._checkHeartbeatTimeout(), 30000);
    if (this.heartbeatTimeout.unref) this.heartbeatTimeout.unref();
  }

  // === 连接中断重连 ===

  _onWsClosed() {
    this.connected = false;
    clearInterval(this.heartbeatInterval);
    this.heartbeatInterval = null;
    if (!this.closing) this._requestReconnect('ws closed');
  }

  async _requestReconnect(reason) {
    if (this.closing) return;
    console.log(`[CDP] 连接中断: ${reason} — 重连中...`);
    clearInterval(this.heartbeatInterval);
    this.heartbeatInterval = null;
    try {
      const targets = await this._getTargets();
      const page = targets.find(t => t.type === 'page' && !t.url.startsWith('devtools://') && !t.url.startsWith('chrome://'));
      if (page) this.targetId = page.targetId;
      else {
        const created = await this._createTarget('about:blank');
        this.targetId = created.targetId;
      }

      const wsUrl = `ws://${this.host}:${this.port}/devtools/page/${this.targetId}`;
      await this._connectWS(wsUrl);

      await this.send('Runtime.enable');
      await this.send('Network.enable');
      await this.send('Page.enable');
      await this.send('DOM.enable');
      this.connected = true;
      this.lastHeartbeat = Date.now();
      this._startHeartbeat();
      console.log('[CDP] 重连成功，目标:', this.targetId);
    } catch (e) {
      console.log('[CDP] 重连失败:', e.message);
      if (!this.closing) { const t = setTimeout(() => this._requestReconnect('retry'), 5000); if (t.unref) t.unref(); }
    }
  }

  // === CDP 命令 ===

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      if (!this.ws || this.ws.readyState !== wsClass.OPEN) return reject(new Error('CDP not connected'));
      const id = ++this.msgId;
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => { if (this.pending.has(id)) { this.pending.delete(id); reject(new Error('CDP timeout: ' + method)); } }, 30000);
    });
  }

  // === 导航 ===

  async nav(url, waitUntil = 'networkidle2', timeout = 30000) {
    await this.send('Page.navigate', { url });
    if (waitUntil === 'networkidle2') {
      await this.send('Network.setCacheDisabled', { cacheDisabled: true });
      await this.wait(2000);
    }
    return this;
  }

  wait(ms) { return new Promise(r => setTimeout(r, ms)); }

  // === JS 执行 ===

  async js(code, awaitPromise = true) {
    const res = await this.send('Runtime.evaluate', { expression: code, awaitPromise, returnByValue: true, userGesture: true });
    if (res.exceptionDetails) throw new Error(res.exceptionDetails.text);
    return res.result?.value;
  }

  // === 点击 ===

  async click(selector, options = {}) {
    const box = await this.js(`( () => { const el = document.querySelector(${JSON.stringify(selector)}); if (!el) return null; const r = el.getBoundingClientRect(); return { x: r.left + r.width/2, y: r.top + r.height/2 }; })() `);
    if (!box) throw new Error('Element not found: ' + selector);
    await this.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x, y: box.y, button: 'left', clickCount: 1, ...options });
    await this.wait(100);
    await this.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x, y: box.y, button: 'left', clickCount: 1, ...options });
    return this;
  }

  // === 输入文本 ===

  async input(selector, text, options = {}) {
    await this.click(selector);
    await this.wait(100);
    await this.send('Input.dispatchKeyEvent', { type: 'keyDown', modifiers: 2, key: 'a', code: 'KeyA' });
    await this.send('Input.dispatchKeyEvent', { type: 'keyUp', modifiers: 2, key: 'a', code: 'KeyA' });
    await this.wait(50);
    for (const ch of text) { await this.send('Input.insertText', { text: ch }); await this.wait(options.delay || 30); }
    return this;
  }

  // === 滚动 ===

  async scroll(x = 0, y = 500) { await this.js('window.scrollBy(' + x + ', ' + y + ')'); return this; }

  // === 截图 ===

  async screenshot({ format = 'png', quality = 80 } = {}) {
    const res = await this.send('Page.captureScreenshot', { format, quality });
    return Buffer.from(res.data, 'base64');
  }

  // === 关闭 ===

  async close() {
    this.closing = true;
    clearInterval(this.heartbeatInterval);
    clearTimeout(this.heartbeatTimeout);
    this.heartbeatInterval = null;
    const w = this.ws;
    this.ws = null;
    this.connected = false;
    if (w) { try { w.close(); } catch (e) {} }
  }
}

// === 便捷函数 ===

async function withCDP(fn, options) {
  const cdp = new CDP(options);
  await cdp.connect();
  try { return await fn(cdp); } finally { await cdp.close(); }
}

module.exports = { CDP, withCDP };