// arcade-extra.js — 独立路由:排行榜 /api/rank + 自动心得 /api/reflect + 反馈 /api/feedback + 告警 /api/alert
// 修改记录:
//   2026-10-11 弃用 global.kv(Workers 风格),改用 KV REST(Upstash),与 alipay.js 同源契约
//   SMTP 告警从 /api/notify 迁移到 /api/alert(原 /api/notify 保留为支付宝回调)
'use strict';

const env = k => process.env[k] || '';

function rest(){
  const u = env('KV_REST_API_URL') || env('UPSTASH_REDIS_REST_URL');
  const t = env('KV_REST_API_TOKEN') || env('UPSTASH_REDIS_REST_TOKEN');
  return (u && t) ? { u: u.replace(/\/$/, ''), t } : null;
}

async function cmd(segs){
  const r = rest();
  if(!r) throw new Error('no-kv');
  const url = r.u + '/' + segs.map(s => encodeURIComponent(String(s))).join('/');
  const res = await fetch(url, { headers: { Authorization: 'Bearer ' + r.t }, signal: AbortSignal.timeout(7000) });
  const j = await res.json();
  return (j && j.result !== undefined) ? j.result : null;
}

async function kvGet(k){ try{ return await cmd(['get', k]); }catch(e){ return null; } }

async function kvScan(pattern, cap){
  const out = [];
  let cursor = '0';
  for(let i = 0; i < 30 && out.length < cap; i++){
    let res = null;
    try{ res = await cmd(['scan', cursor, 'MATCH', pattern, 'COUNT', '200']); }catch(e){ break; }
    if(!Array.isArray(res) || res.length < 2) break;
    const keys = res[1] || [];
    for(const k of keys){ if(out.length < cap) out.push(k); }
    cursor = String(res[0]);
    if(cursor === '0' || !keys.length) break;
  }
  return out;
}

function storeKind(){ return rest() ? 'kv-rest' : 'none'; }

// ---------- 排行榜 ----------
// 注意：alipay.js 的 dbGet/dbSet 统一加 'bds_' 前缀，故此处键名必须带 bds_ 才同源
const K = k => 'bds_' + k;
async function leader(n, includeRef){
  const balKeys = await kvScan('bds_arc_bal_*', 200);
  const freeKeys = await kvScan('bds_arc_free_*', 200);
  const users = {};
  balKeys.forEach(k => { users[k.slice(('bds_arc_bal_').length)] = 0; });
  freeKeys.forEach(k => { users[k.slice(('bds_arc_free_').length)] = 0; });

  const rows = [];
  for(const ref of Object.keys(users)){
    const bal = parseInt(await kvGet(K('arc_bal_' + ref)) || '0', 10) || 0;
    const free = parseInt(await kvGet(K('arc_free_' + ref)) || '0', 10) || 0;
    const bonus = parseInt(await kvGet(K('arc_bonus_' + ref)) || '0', 10) || 0;
    const total = bal + free + bonus;
    if(total > 0) rows.push({ ref, seconds: total });
  }
  rows.sort((a, b) => b.seconds - a.seconds);
  const top = rows.slice(0, n || 50).map((r, i) => ({
    rank: i + 1,
    minutes: Math.round(r.seconds / 60),
    ref: includeRef === false ? undefined : r.ref
  }));
  return { total: rows.length, top };
}

const TIPS = [
  '\u6bcf\u79d2\u90fd\u7b97\u6570\uff0c\u670d\u52a1\u5668\u8ba1\u65f6\uff0c\u7cbe\u51c6\u80fd\u6536\u6b3e',
  '\u5148\u514d\u8d39\u540e\u4ed8\u8d39\uff0c\u65f6\u957f\u662f\u771f\u91d1\u767d\u94f6',
  '\u522b\u6539\u672c\u5730\uff0c\u670d\u52a1\u5668\u91cc\u7684\u624d\u7b97\uff0c\u5fc3\u8df3\u76d1\u63a7\u957f\u671f',
  '\u591a\u9080\u8bf7\uff0c\u7b2c\u4e00\u540d\u6709\u5956\u52f4\uff0c\u597d\u611f\u4e0d\u53ef\u4fee\u6539'
];
function reflect(secs, total){
  if(total < 2) return '\u6392\u884c\u699c\u4eba\u6570\u4e0d\u8db3\uff0c\u5148\u9080\u8bf7\u670b\u53cb\u4e00\u8d77\u73a9\u5427';
  return '\u81ea\u52a8\u5fc3\u5f97 #' + (secs % TIPS.length + 1) + ' ' + TIPS[secs % TIPS.length];
}

// ---------- SMTP 告警(QQ 465, AUTH LOGIN) ----------
function smtp(subject, body){
  return new Promise(resolve => {
    const H = env('SMTP_HOST') || 'smtp.qq.com';
    const P = parseInt(env('SMTP_PORT') || '465', 10);
    const U = env('SMTP_USER') || '';
    const PASS = env('SMTP_AUTH') || '';
    const TO = env('SMTP_TO') || U;
    if(!U || !PASS) return resolve({ ok:false, reason:'smtp_unconfigured' });
    const b64 = s => Buffer.from(String(s), 'utf8').toString('base64');
    const tls = require('tls');
    let st = 0, buf = '', done = false, sock = null;
    const line = s => { try{ sock.write(s + '\r\n'); }catch(e){} };
    const finish = (ok, info) => { if(done) return; done = true;
      try{ sock && sock.end(); }catch(e){}
      resolve({ ok, info: info || '' });
    };
    sock = tls.connect({ host: H, port: P, servername: H }, () => {
      sock.on('data', d => {
        buf += d.toString('latin1');
        let i;
        while((i = buf.indexOf('\r\n')) >= 0){
          const raw = buf.slice(0, i); buf = buf.slice(i + 2);
          const code = parseInt(raw, 10);
          if(code === 220 && st === 0) line('EHLO arcade-extra'), st = 1;
          else if(code === 250 && st === 1) line('AUTH LOGIN'), st = 2;
          else if(code === 334 && st === 2) line(b64(U)), st = 3;
          else if(code === 334 && st === 3) line(b64(PASS)), st = 4;
          else if(code === 235 && st === 4) line(`MAIL FROM:<${U}>`), st = 5;
          else if(code === 250 && st === 5) line(`RCPT TO:<${TO}>`), st = 6;
          else if(code === 250 && st === 6) line('DATA'), st = 7;
          else if(code === 354 && st === 7){
            line(`Subject: ${subject}\r\nFrom: ${U}\r\nTo: ${TO}\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n${body}\r\n.`);
            st = 8;
          }
          else if(code === 250 && st === 8){ line('QUIT'); finish(true); }
          else if(code >= 500){ finish(false, 'smtp_' + code); }
          if(done) buf = '';
        }
      });
    });
    sock.on('error', e => finish(false, String(e && e.message || e)));
    sock.setTimeout(10000, () => finish(false, 'timeout'));
  });
}

/* Webhook 中继：Vercel 机房 IP 直连 QQ SMTP 必 535 → 转发到本机(家宽 IP)代发邮件 */
async function webhookRelay(subject, body){
  try{
    const url = process.env.ALERT_WEBHOOK_URL || '';
    if(!url) return { ok:false, reason:'no_webhook_url' };
    const headers = { 'content-type':'application/json' };
    if(process.env.ALERT_WEBHOOK_TOKEN) headers['x-alert-token'] = process.env.ALERT_WEBHOOK_TOKEN;
    const r = await fetch(url, { method:'POST', headers,
      body: JSON.stringify({ subject, message: String(body).slice(0, 2000) }),
      signal: AbortSignal.timeout(20000) });
    const j = await r.json().catch(() => ({}));
    return { ok: r.ok && (j.ok === true || j.status === 'ok'), reason: j.reason || ('http_' + r.status) };
  }catch(e){ return { ok:false, reason: String(e && e.message || e) }; }
}

// ---------- 反馈落库 ----------
async function saveFeedback(text){
  const rec = { text: String(text).slice(0, 2000), at: new Date().toISOString() };
  const k = 'arc_fb_' + Date.now();
  try{
    const r = rest();
    if(r){
      await fetch(r.u + '/set/' + encodeURIComponent(k), {
        method: 'POST',
        headers: { Authorization: 'Bearer ' + r.t, 'Content-Type': 'application/json' },
        body: JSON.stringify(rec),
        signal: AbortSignal.timeout(5000)
      });
    }
  }catch(e){}
  return true;
}

module.exports = async function(req, res){
  try{
    const u = new URL(req.url || '/', 'http://x');
    const p = u.pathname;
    const send = (code, obj) => { try{ res.writeHead(code, {'Content-Type':'application/json; charset=utf-8'}); res.end(JSON.stringify(obj)); }catch(e){} };

    if(p === '/api/rank'){
      const top = await leader(50, u.searchParams.get('ref') !== '1' || true);
      return send(200, { ok:true, store: storeKind(), total: top.total, at: Date.now(), top: top.top.slice(0, 10) });
    }
    if(p === '/api/reflect'){
      const ref = (u.searchParams.get('ref') || '').slice(0, 48);
      const top = await leader(50, true);
      const i = top.top.findIndex(r => r.ref === ref);
      const secs = i >= 0 ? (i * 7) % 31 : 24;
      return send(200, {
        ok: true,
        rank: i >= 0 ? i + 1 : top.total + 1,
        total: top.total,
        reflect: reflect(secs, top.total)
      });
    }
    if(p === '/api/feedback'){
      let b = '';
      req.on('data', d => b += d);
      req.on('end', async () => {
        let text = '';
        try{ text = String((JSON.parse(b || '{}') || {}).text || '').slice(0, 2000); }catch(e){}
        await saveFeedback(text);
        send(200, { ok: true, received: text.length, at: Date.now() });
      });
      return;
    }
    // 服务端待付单（AutoOps 订单挽回用）：写/读/清 arc_pend_<ref>，需密钥，绝不触碰计费锚点
    if(p === '/api/pending'){
      const want = env('AUTOOPS_SECRET');
      if(!want || u.searchParams.get('k') !== want) return send(403, { ok:false, error:'forbidden' });
      const ref = (u.searchParams.get('ref') || '').slice(0, 32);
      if(!ref) return send(200, { ok:false, error:'missing ref' });
      const op = u.searchParams.get('op') || 'get';
      if(op === 'clear'){
        const rr = rest();
        if(rr){ try{
          await fetch(rr.u + '/set/' + encodeURIComponent(K('arc_pend_' + ref)), {
            method: 'POST', headers: { Authorization: 'Bearer ' + rr.t, 'Content-Type': 'application/json' },
            body: JSON.stringify({ cleared_at: new Date().toISOString(), expires_at: 0 }),
            signal: AbortSignal.timeout(5000)
          });
        }catch(e){} }
        return send(200, { ok:true, cleared:true });
      }
      if(op === 'set'){
        const plan = (u.searchParams.get('plan') || '').slice(0, 20);
        const amount = (u.searchParams.get('amount') || '').slice(0, 12);
        const pct = Math.max(0, Math.min(100, parseInt(u.searchParams.get('pct') || '0', 10) || 0));
        const out = (u.searchParams.get('out_trade_no') || '').slice(0, 80);
        if(!plan || !amount) return send(200, { ok:false, error:'missing plan/amount' });
        const rec = { plan, amount, pct, out_trade_no: out, expires_at: Date.now() + 24 * 3600 * 1000, created_at: new Date().toISOString() };
        const rr = rest();
        if(!rr) return send(200, { ok:false, error:'no-kv' });
        try{
          const resp = await fetch(rr.u + '/set/' + encodeURIComponent(K('arc_pend_' + ref)), {
            method: 'POST', headers: { Authorization: 'Bearer ' + rr.t, 'Content-Type': 'application/json' },
            body: JSON.stringify(rec), signal: AbortSignal.timeout(5000)
          });
          return send(200, { ok: resp.ok, store: storeKind(), rec });
        }catch(e){ return send(200, { ok:false, error: String(e && e.message || e) }); }
      }
      const v = await kvGet(K('arc_pend_' + ref));
      return send(200, { ok:true, store: storeKind(), ref, pending: v });
    }
    if(p === '/api/alert'){
      const topic = String(u.searchParams.get('topic') || 'general').slice(0, 80);
      const msg = String(u.searchParams.get('msg') || 'ping').slice(0, 500);
      const r = await smtp('[arcade-extra] ' + topic, msg);
    // Vercel 机房 IP 直连 QQ SMTP 会 535 → 改由本机中继代发
    let relayed = { ok:false, reason:'skipped' };
    if(!r.ok){ relayed = await webhookRelay('[arcade-extra] ' + topic, msg); }
      // 兜底：无论 SMTP 成败，都持久化到 KV，供 AutoOps /api/autoops.js?a=alerts 读取
      let persisted = false;
      try{
        const req2 = rest();
        if(req2){
          const k = 'bds_alert_' + topic + '_' + Date.now();
          const resp = await fetch(req2.u + '/set/' + encodeURIComponent(k), {
            method: 'POST',
            headers: { Authorization: 'Bearer ' + req2.t, 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic, message: msg, at: new Date().toISOString(), smtp_ok: !!r.ok, smtp_reason: r.reason || r.info || '' }),
            signal: AbortSignal.timeout(5000)
          });
          persisted = resp.ok;
        }
      }catch(e){}
      return send(r.ok ? 200 : 502, {
        ok: !!r.ok,
        reason: r.reason || r.info || '',
        persisted: persisted,
        channel: r.ok ? 'smtp' : (relayed.ok ? 'webhook' : (persisted ? 'kv_fallback' : 'none'))
      });
    }
    return send(404, { ok:false, error: 'arcade-extra no route', path: p });
  }catch(e){
    return send(500, { ok:false, error: String(e && e.message || e) });
  }
};