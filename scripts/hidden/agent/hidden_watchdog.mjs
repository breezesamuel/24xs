#!/usr/bin/env node
/**
 * hidden_watchdog.mjs — 运维巡检（无静默失败 / 主动告警）
 *
 * 对标最佳实践（Millwright watchdog / Sokko health check / GitHub Actions
 * pipeline-health-check）：每分钟/每 tick 确定性扫描关键信号，异常即告警，
 * 绝不静默失败。
 *
 * 检查项：
 *   1. 编排器心跳新鲜度（state/heartbeat.json / state.json）
 *   2. 真实收银台健康（/api/health + 支付凭据是否就绪）
 *   3. 真实支付转化异常（订单>0 但 paid=0 持续）
 *   4. 推广队列积压（CDP 持续离线且 pending 高）
 *   5. 关键数据文件缺失/为空
 *   6. 凭据缺失（GH_TOKEN/AI_KEY）→ 降级提示
 * 告警通道：SMTP（QQ 465）+ autoops/hidden/real_alerts.jsonl（审计+去重）
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import tls from 'tls';
import { episodic } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const ALERTS = path.join(H, 'real_alerts.jsonl');
const STOREFRONT = process.env.STOREFRONT_BASE || 'https://tools.highkingflower.com';

function load(p){ if(!fs.existsSync(p)) return []; try{ return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }catch(e){ return []; } }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function now(){ return new Date().toISOString(); }
function read(p){ try{ return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p,'utf8')) : null; }catch(e){ return null; } }

/* ---------- 告警：SMTP + 去重（同类告警 6 小时内不重复轰炸） ---------- */
const COOLDOWN_MS = 6 * 60 * 60 * 1000;
function recentAlert(kind){
  const recent = load(ALERTS).filter(a => Date.now() - new Date(a.at).getTime() < COOLDOWN_MS);
  return recent.some(a => a.kind === kind && a.alerted === true);
}
function record(kind, msg, alerted, why){
  append(ALERTS, { at: now(), kind, msg: String(msg).slice(0, 300), alerted, reason: why, auto: true });
}
function smtp(subject, body){
  return new Promise(resolve => {
    const host = process.env.SMTP_HOST || '';
    const port = parseInt(process.env.SMTP_PORT || '465', 10);
    const user = process.env.SMTP_USER || '';
    const pass = process.env.SMTP_AUTH || '';
    const to = process.env.SMTP_TO || user;
    if(!host || !user || !pass) return resolve({ ok:false, reason:'smtp_unconfigured' });
    const b64 = s => Buffer.from(String(s), 'utf8').toString('base64');
    let st = 0, buf = '', done = false, sock = null;
    const line = s => { try{ sock.write(s + '\r\n'); }catch(e){} };
    const finish = (ok, info) => { if(done) return; done = true; try{ sock && sock.end(); }catch(e){} resolve({ ok, info: info || '' }); };
    sock = tls.connect({ host, port, servername: host }, () => {
      sock.on('data', d => {
        buf += d.toString('latin1');
        let i;
        while((i = buf.indexOf('\r\n')) >= 0){
          const raw = buf.slice(0, i); buf = buf.slice(i + 2);
          const code = parseInt(raw, 10);
          if(code === 220 && st === 0) line('EHLO watchdog'), st = 1;
          else if(code === 250 && st === 1) line('AUTH LOGIN'), st = 2;
          else if(code === 334 && st === 2) line(b64(user)), st = 3;
          else if(code === 334 && st === 3) line(b64(pass)), st = 4;
          else if(code === 235 && st === 4) line(`MAIL FROM:<${user}>`), st = 5;
          else if(code === 250 && st === 5) line(`RCPT TO:<${to}>`), st = 6;
          else if(code === 250 && st === 6) line('DATA'), st = 7;
          else if(code === 354 && st === 7){ line(`Subject: ${subject}\r\nFrom: ${user}\r\nTo: ${to}\r\nContent-Type: text/plain; charset=UTF-8\r\n\r\n${body}\r\n.`); st = 8; }
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

async function alert(kind, subject, msg){
  if(recentAlert(kind)){ record(kind, msg, false, 'cooldown_suppressed'); return 'suppressed'; }
  const r = await smtp(subject, msg);
  record(kind, msg, true, r.ok ? 'smtp_sent' : `smtp_failed:${r.reason || r.info}`);
  return r.ok ? 'sent' : 'smtp_failed';
}

/* ---------- 检查项实现 ---------- */
async function checkHeartbeat(){
  const hb = read(path.join(H, 'state/heartbeat.json'));
  const st = read(path.join(H, 'state.json'));
  const hbAt = hb && hb.last_heartbeat ? new Date(hb.last_heartbeat).getTime() : null;
  const stAt = st && st.last_tick ? new Date(st.last_tick).getTime() : null;
  const freshest = Math.max(hbAt || 0, stAt || 0);
  const ageMin = freshest ? (Date.now() - freshest) / 60000 : Infinity;
  if(!freshest){
    await alert('stale_heartbeat_none', '[watchdog] 编排器从未心跳', 'state/heartbeat.json 与 state.json 均缺失或无效');
    return { ok:false, age_min: null };
  }
  if(ageMin > 60){
    await alert('stale_heartbeat', '[watchdog] 编排器心跳过期',
      `最近心跳距今 ${ageMin.toFixed(0)} 分钟（阈值 60 分钟）。可能 GitHub Actions / Vercel cron 未触发。`);
    return { ok:false, age_min: Math.round(ageMin) };
  }
  return { ok:true, age_min: Math.round(ageMin) };
}

async function checkStorefront(){
  try{
    const res = await fetch(`${STOREFRONT}/api/health`, { signal: AbortSignal.timeout(20000) });
    if(!res.ok){
      await alert('storefront_down', '[watchdog] 收银台不可用', `/api/health HTTP ${res.status}`);
      return { ok:false, http: res.status };
    }
    const j = await res.json();
    const env = j.env || {};
    if(!(env.app && env.priv && env.pub)){
      await alert('storefront_unready', '[watchdog] 收银台凭据未就绪',
        `/api/health env=${JSON.stringify(env)} —— 无法真实收款！`);
      return { ok:false, env };
    }
    return { ok:true, env };
  }catch(e){
    await alert('storefront_down', '[watchdog] 收银台探测失败', String(e && e.message || e).slice(0, 200));
    return { ok:false, error: String(e && e.message || e).slice(0, 120) };
  }
}

async function checkConversion(){
  const rows = load(path.join(H, 'real_metrics.jsonl'));
  const recent = rows.slice(-3).map(r => r.orders);
  const allZero = recent.length >= 2 && recent.every(o => o && o.total > 0 && o.paid === 0);
  if(allZero){
    const total = recent[recent.length - 1].total;
    await alert('zero_paid_streak', '[watchdog] 连续无支付',
      `最近 ${recent.length} 次拉取：订单 ${total} 笔但 paid=0。需检查支付流程/获客质量。`);
    return { ok:false, streak: recent.length };
  }
  return { ok:true };
}

async function checkPromoQueue(){
  const rows = load(path.join(H, 'real_acquisition.jsonl')).slice(-3);
  const stuck = rows.length >= 2 && rows.every(r => r && r.cdp_online === false);
  const pending = rows.length ? rows[rows.length - 1].pending : 0;
  if(stuck && pending > 0){
    await alert('promo_queue_stuck', '[watchdog] 推广队列积压',
      `CDP 连续 ${rows.length} 次离线，${pending} 篇推广无法分发 → 零流量 → 零营收。请启动 CDP(:9223) 已登录浏览器。`);
    return { ok:false, pending };
  }
  return { ok:true, pending };
}

async function checkFiles(){
  const critical = [
    'real_metrics.jsonl', 'real_orders.jsonl', 'crm_auto.jsonl',
    'leads_auto.jsonl', 'payments_auto.jsonl'
  ];
  const missing = critical.filter(f => !fs.existsSync(path.join(H, f)) || fs.statSync(path.join(H, f)).size === 0);
  if(missing.length){
    await alert('files_missing', '[watchdog] 关键数据文件异常', `缺失或为空: ${missing.join(', ')}`);
    return { ok:false, missing };
  }
  return { ok:true };
}

function checkCredentials(){
  const gh = process.env.GH_TOKEN && !String(process.env.GH_TOKEN).includes('placeholder');
  const ai = process.env.OPENROUTER_API_KEY || process.env.AI_API_KEY;
  const missing = [];
  if(!gh) missing.push('GH_TOKEN');
  if(!ai) missing.push('OPENROUTER_API_KEY');
  // 凭据缺失是已知降级项，仅记录不告警（避免每日轰炸）
  record('credentials_missing', missing.join(','), false, missing.length ? 'degraded' : 'ok');
  return { ok: missing.length === 0, missing };
}

async function main(){
  if(!fs.existsSync(H)) fs.mkdirSync(H, { recursive: true });
  const [hb, sf, conv, promo, files, creds] = await Promise.all([
    checkHeartbeat(), checkStorefront(), checkConversion(), checkPromoQueue(), checkFiles(), checkCredentials()
  ]);
  const allOk = hb.ok && sf.ok && conv.ok && promo.ok && files.ok;
  const report = {
    at: now(), heartbeat: hb, storefront: sf, conversion: conv, promo: promo, files: files, credentials: creds,
    overall: allOk ? 'healthy' : 'degraded'
  };
  append(path.join(H, 'watchdog.jsonl'), report);
  episodic('hidden_watchdog', { overall: report.overall });
  console.log(`[hidden_watchdog] ${report.overall} (hb=${hb.ok} storefront=${sf.ok} conv=${conv.ok} promo=${promo.ok} files=${files.ok} creds=${creds.ok})`);
}

main().catch(e => {
  console.log(`[hidden_watchdog] error: ${e.message}`);
  episodic('hidden_watchdog_error', { error: String(e && e.message || e) });
});