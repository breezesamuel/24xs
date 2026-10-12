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
import http from 'http';
import { fileURLToPath } from 'url';
import tls from 'tls';
import { episodic } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const ALERTS = path.join(H, 'real_alerts.jsonl');
const HEALTH = path.join(H, 'health_status.json');
const STOREFRONT = process.env.STOREFRONT_BASE || 'https://tools.highkingflower.com';

// 写入开关：只读查询（可视化大屏轮询）时关闭，避免触发告警邮件与审计刷屏
let ALERTS_ENABLED = true;   // 是否允许发送告警
let AUDIT_ENABLED = true;    // 是否允许写入 real_alerts.jsonl

function load(p){ if(!fs.existsSync(p)) return []; try{ return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }catch(e){ return []; } }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function now(){ return new Date().toISOString(); }
function read(p){ try{ return fs.existsSync(p) ? JSON.parse(fs.readFileSync(p,'utf8')) : null; }catch(e){ return null; } }

// 判断是否"首跑环境"：state.json 是编排器完成一个 tick 后的自标记。
// GitHub Actions / 新机器上它不存在 → 首跑，缺文件/缺心跳属正常，
// 不应判定为核心故障（否则每次运行都会误报告警）。
function isFreshEnv(){
  return !fs.existsSync(path.join(H, 'state.json'));
}

/* ---------- 告警：SMTP + 去重（同类 6h 不重复）+ 升级 + 恢复 ---------- */
const COOLDOWN_MS = 6 * 60 * 60 * 1000;
// 连续失败达到阈值后升级告警（绕过 6h 去重，但受升级冷却限制，避免 15 分钟编排刷屏）
const ESCALATE_AFTER = parseInt(process.env.WATCHDOG_ESCALATE_AFTER || '3', 10);
const ESCALATE_COOLDOWN_MS = parseInt(process.env.WATCHDOG_ESCALATE_COOLDOWN_MS || String(2 * 60 * 60 * 1000), 10);
const ALERT_STATE = path.join(H, 'alert_state.json');
const FAILING = new Set();   // 本次巡检判定失败的告警 kind（供升级/恢复判定）
function recentAlert(kind){
  const recent = load(ALERTS).filter(a => Date.now() - new Date(a.at).getTime() < COOLDOWN_MS);
  return recent.some(a => a.kind === kind && a.alerted === true);
}
function record(kind, msg, alerted, why){
  if(!AUDIT_ENABLED) return;
  append(ALERTS, { at: now(), kind, msg: String(msg).slice(0, 300), alerted, reason: why, auto: true });
}
function readAlertState(){ try{ return JSON.parse(fs.readFileSync(ALERT_STATE, 'utf8')); }catch(e){ return {}; } }
function writeAlertState(s){ try{ fs.writeFileSync(ALERT_STATE, JSON.stringify(s, null, 2)); }catch(e){} }
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

/* KV 兜底告警通道：SMTP 失败时 POST 到收银台 /api/alert（内部写 KV，供 autoops.js?a=alerts 读取） */
async function kvFallback(subject, body){
  try{
    const url = `${STOREFRONT}/api/alert?topic=${encodeURIComponent(('watchdog: ' + subject).slice(0, 120))}&msg=${encodeURIComponent(String(body).slice(0, 900))}`;
    const r = await fetch(url, { method: 'POST', signal: AbortSignal.timeout(15000) });
    const j = await r.json().catch(() => ({}));
    const channel = j.channel || ('http_' + r.status);
    return { ok: !!(j.ok === true || channel === 'kv_fallback'), channel, reason: j.reason || ('http_' + r.status) };
  }catch(e){ return { ok: false, channel: 'error', reason: String(e && e.message || e) }; }
}
/** 发送告警：优先 SMTP，失败则 KV 兜底。返回 { ok, channel } */
async function notify(subject, body){
  const r = await smtp(subject, body);
  if(r.ok) return { ok: true, channel: 'smtp' };
  const kv = await kvFallback(subject, body);
  return { ok: kv.ok, channel: kv.ok ? 'kv_fallback' : 'none', smtp: r.reason || r.info || '', reason: kv.reason || '' };
}

async function alert(kind, subject, msg){
  FAILING.add(kind);   // 记录失败（即使被去重/只读抑制），供升级与恢复判定   // 记录失败（即使被去重/只读抑制），供升级与恢复判定
  if(!ALERTS_ENABLED) return 'suppressed';
  if(recentAlert(kind)){ record(kind, msg, false, 'cooldown_suppressed'); return 'suppressed'; }
  const r = await notify(subject, msg);
  record(kind, msg, true, r.ok ? `${r.channel}_sent` : `notify_failed:smtp=${r.smtp || ''};kv=${r.reason || ''}`);
  return r.ok ? r.channel : 'failed';
}

/**
 * 升级 + 恢复：
 *   - 每个 kind 连续失败计数（跨运行持久化于 alert_state.json）
 *   - 连续失败 >= ESCALATE_AFTER 且距上次升级 > ESCALATE_COOLDOWN_MS → 发送升级邮件（WARN/CRITICAL）
 *   - 上次在告警、本次已恢复 → 发送一次恢复通知，并清零计数
 * 仅在 main() 路径调用（只读 getHealthStatus 不触发）。
 */
async function handleAlerts(){
  const st = readAlertState();
  const active = new Set(FAILING);

  for(const kind of active){
    const prev = st[kind] || { count: 0, active: false, last_escalated_at: null };
    const count = (prev.active ? (prev.count || 0) : 0) + 1;
    const rec = { count, active: true, last_fail_at: now(), last_escalated_at: prev.last_escalated_at || null };
    if(count >= ESCALATE_AFTER){
      const last = rec.last_escalated_at ? new Date(rec.last_escalated_at).getTime() : 0;
      if(Date.now() - last > ESCALATE_COOLDOWN_MS){
        const lvl = count >= ESCALATE_AFTER * 2 ? 'CRITICAL' : 'WARN';
        const r = await notify(`[watchdog ESCALATED ×${count} ${lvl}] ${kind}`,
          `故障未修复：${kind} 已连续失败 ${count} 次。\n最近失败：${rec.last_fail_at}\n阈值 ${ESCALATE_AFTER}，升级冷却 ${(ESCALATE_COOLDOWN_MS / 3600000).toFixed(1)}h。请立即处理。`);
        record(kind, `escalated ×${count} ${lvl}`, true, r.ok ? `${r.channel}_sent` : `escalate_failed:${r.smtp || r.reason || ''}`);
        rec.last_escalated_at = now();
      }
    }
    st[kind] = rec;
  }

  for(const kind of Object.keys(st)){
    const prev = st[kind];
    if(prev && prev.active && !active.has(kind)){
      const r = await notify(`[watchdog RECOVERED] ${kind}`, `${kind} 已恢复（此前连续失败 ${prev.count || 0} 次）。`);
      record(kind, `recovered after ${prev.count || 0} fails`, true, r.ok ? `${r.channel}_sent` : `recovery_failed:${r.smtp || r.reason || ''}`);
      st[kind] = { count: 0, active: false, last_fail_at: prev.last_fail_at || null, last_escalated_at: null, recovered_at: now() };
    }
  }

  writeAlertState(st);
  return { active_failures: Array.from(active) };
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
    // 首跑环境（Actions 全新 checkout / 新机器）：心跳缺失属正常，不算故障
    if(isFreshEnv()){
      record('heartbeat_absent', 'fresh environment: no prior tick yet', false, 'bootstrap');
      return { ok:true, note: 'fresh_environment' };
    }
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

async function checkAlertChannel(){
  // 探测告警通道：SMTP 有效性 + KV 兜底可用性
  try{
    const res = await fetch(`${STOREFRONT}/api/alert?topic=watchdog-probe&msg=channel-probe`, { signal: AbortSignal.timeout(25000) });
    const j = await res.json().catch(() => ({}));
    const ch = j.channel || (j.ok ? 'smtp' : 'unknown');
    if(ch === 'kv_fallback' || ch === 'none' || ch === 'unknown'){
      await alert('smtp_broken', '[watchdog] SMTP 告警通道失效',
        `SMTP 认证失败（${j.reason || 'unknown'}），告警已降级为 KV 兜底通道。\n`
        + `修复：登录 QQ 邮箱 → 设置 → 账户 → 开启 SMTP 服务 → 生成新授权码 → 更新 SMTP_AUTH（16位）。`);
      return { ok:false, channel: ch, smtp_reason: j.reason || '' };
    }
    return { ok:true, channel: ch };
  }catch(e){
    await alert('alert_channel_down', '[watchdog] 告警通道探测失败', String(e && e.message || e).slice(0, 200));
    return { ok:false, error: String(e && e.message || e).slice(0, 120) };
  }
}

async function checkPromoQueue(){
  const rows = load(path.join(H, 'real_acquisition.jsonl')).slice(-3);
  const stuck = rows.length >= 2 && rows.every(r => r && r.cdp_online === false);  const pending = rows.length ? rows[rows.length - 1].pending : 0;
  if(stuck && pending > 0){
    await alert('promo_queue_stuck', '[watchdog] 推广队列积压',
      `CDP 连续 ${rows.length} 次离线，${pending} 篇推广无法分发 → 零流量 → 零营收。请启动 CDP(:9223) 已登录浏览器。`);
    return { ok:false, pending };
  }
  return { ok:true, pending };
}

async function checkFiles(){
  // 关键数据文件：由每次编排的核心阶段产出，缺失=真实数据丢失
  const critical = [
    'real_metrics.jsonl', 'real_orders.jsonl', 'crm_auto.jsonl', 'leads_auto.jsonl'
  ];
  // 可选文件：仅在真实事件发生后才出现（如首笔支付），缺失属正常，不判 critical
  const optional = ['payments_auto.jsonl'];
  const missing = critical.filter(f => !fs.existsSync(path.join(H, f)));
  const empty = critical.concat(optional).filter(f => fs.existsSync(path.join(H, f)) && fs.statSync(path.join(H, f)).size === 0);
  // 只要有文件真正缺失 → 严格 critical（数据丢失）
  if(missing.length){
    if(isFreshEnv()){
      record('files_missing', 'fresh environment: ' + missing.join(','), false, 'bootstrap');
      return { ok:true, note: 'fresh_environment', missing };
    }
    await alert('files_missing', '[watchdog] 关键数据文件彻底丢失', `缺失: ${missing.join(', ')}`);
    return { ok:false, missing };
  }
  // 文件存在但为空 → 在早期/无凭据运行阶段属正常过渡状态，不算核心故障
  if(empty.length > 0 && !isFreshEnv()){
    record('files_empty', '[watchdog] 数据文件空置: ' + empty.join(','), false, 'transition');
  }
  return { ok: missing.length === 0 };
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

// 运行 7 项巡检（副作用受 ALERTS_ENABLED/AUDIT_ENABLED 控制）
async function runChecks(){
  FAILING.clear();
  const [hb, sf, conv, promo, files, creds, alertCh] = await Promise.all([
    checkHeartbeat(), checkStorefront(), checkConversion(), checkPromoQueue(), checkFiles(), checkCredentials(), checkAlertChannel()
  ]);

  // 关键故障（会导致零营收/零数据）→ 非零退出码，GitHub Actions 自动发免费告警邮件
  const critical = [];
  if(!sf.ok) critical.push('storefront_unhealthy_or_unready');
  if(!files.ok) critical.push('critical_files_missing');
  if(hb.ok === false && hb.age_min !== null) critical.push('heartbeat_stale');
  else if(hb.ok === false && hb.age_min === null) critical.push('heartbeat_absent');

  // 降级项（不阻断，记录+追踪）
  const degraded = [];
  if(!conv.ok) degraded.push('zero_paid_streak');
  if(!promo.ok) degraded.push('promo_queue_stuck');
  if(!creds.ok) degraded.push('credentials_missing:' + creds.missing.join('+'));
  if(!alertCh.ok) degraded.push('alert_channel:' + (alertCh.channel || 'error'));

  return { hb, sf, conv, promo, files, creds, alertCh, critical, degraded };
}

// 标准化健康 JSON（7 项：心跳/收银台/转化/推广/文件/凭据/告警），供可视化大屏消费
function formatHealth(r){
  return {
    at: now(),
    overall: r.critical.length ? 'critical' : (r.degraded.length ? 'degraded' : 'healthy'),
    exit_code: r.critical.length ? 1 : 0,
    checks: {
      heartbeat:     { ok: !!r.hb.ok, age_min: r.hb.age_min ?? null, note: r.hb.note || null },
      storefront:    { ok: !!r.sf.ok, env: r.sf.env || null, http: r.sf.http || null, error: r.sf.error || null },
      conversion:    { ok: !!r.conv.ok, streak: r.conv.streak || 0 },
      promo:         { ok: !!r.promo.ok, pending: r.promo.pending ?? 0 },
      files:         { ok: !!r.files.ok, missing: r.files.missing || [], note: r.files.note || null },
      credentials:   { ok: !!r.creds.ok, missing: r.creds.missing || [] },
      alert_channel: { ok: !!r.alertCh.ok, channel: r.alertCh.channel || null, error: r.alertCh.error || null }
    },
    critical: r.critical,
    degraded: r.degraded,
    active_failures: Array.from(FAILING)
  };
}

// 只读健康查询：默认不告警、不写审计（供大屏/或其他模块 import 调用）
export async function getHealthStatus({ alert: allowAlert = false, audit = false } = {}){
  const prevAlert = ALERTS_ENABLED, prevAudit = AUDIT_ENABLED;
  ALERTS_ENABLED = allowAlert;
  AUDIT_ENABLED = audit;
  try{
    return formatHealth(await runChecks());
  } finally {
    ALERTS_ENABLED = prevAlert;
    AUDIT_ENABLED = prevAudit;
  }
}

async function main(){
  if(!fs.existsSync(H)) fs.mkdirSync(H, { recursive: true });
  const r = await runChecks();
  const report = formatHealth(r);
  const esc = await handleAlerts();   // 升级 + 恢复（持久化连续失败计数）
  report.active_failures = esc.active_failures;

  // 兼容旧格式（watchdog.jsonl）+ 新标准化快照（health_status.json，供大屏读取）
  append(path.join(H, 'watchdog.jsonl'), {
    at: report.at, heartbeat: r.hb, storefront: r.sf, conversion: r.conv, promo: r.promo,
    files: r.files, credentials: r.creds, alert_channel: r.alertCh,
    overall: report.overall, critical: r.critical, degraded: r.degraded, exit_code: report.exit_code,
    active_failures: report.active_failures
  });
  fs.writeFileSync(HEALTH, JSON.stringify(report, null, 2));
  episodic('hidden_watchdog', { overall: report.overall, critical: r.critical.length, degraded: r.degraded.length });
  console.log(`[hidden_watchdog] ${report.overall} (hb=${r.hb.ok} storefront=${r.sf.ok} conv=${r.conv.ok} promo=${r.promo.ok} files=${r.files.ok} creds=${r.creds.ok})`);

  // 关键故障：显式非零退出（GitHub Actions 免费邮件告警通道）
  if(report.exit_code){
    console.log(`[hidden_watchdog] CRITICAL (exit 1 -> Actions email): ${r.critical.join(', ')}`);
    process.exitCode = report.exit_code;
  }
}

// 零依赖健康大屏服务（只读；--serve 启动）。CI/编排器不使用此模式。
const DASHBOARD = path.join(ROOT, 'standards/health_dashboard.html');
async function serve(port = 8787){
  const server = http.createServer(async (req, res) => {
    const url = (req.url || '/').split('?')[0];
    try{
      if(url === '/health' || url === '/api/health'){
        const s = await getHealthStatus({ alert:false, audit:false });
        res.writeHead(200, { 'content-type':'application/json; charset=utf-8' });
        return res.end(JSON.stringify(s, null, 2));
      }
      if(url === '/metrics' || url === '/api/metrics'){
        const metrics = load(path.join(H, 'real_metrics.jsonl')).slice(-20);
        const plan = read(path.join(H, 'hidden_plan.json'));
        res.writeHead(200, { 'content-type':'application/json; charset=utf-8' });
        return res.end(JSON.stringify({ metrics, plan }, null, 2));
      }
      if(url === '/' || url === '/index.html'){
        const html = fs.existsSync(DASHBOARD)
          ? fs.readFileSync(DASHBOARD, 'utf8')
          : '<!doctype html><meta charset="utf-8"><h1>AutoOps</h1><p>dashboard file missing: ' + DASHBOARD + '</p>';
        res.writeHead(200, { 'content-type':'text/html; charset=utf-8' });
        return res.end(html);
      }
      res.writeHead(404, { 'content-type':'text/plain; charset=utf-8' });
      res.end('not found');
    }catch(e){
      res.writeHead(500, { 'content-type':'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: String(e && e.message || e) }));
    }
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', resolve);
  });
  console.log(`[hidden_watchdog] dashboard: http://127.0.0.1:${port}  (Ctrl+C 退出)`);
  return server;
}

// 仅在被直接运行时执行（被 import 时不产生副作用）
const _invokedDirectly = process.argv[1] && path.resolve(process.argv[1]).toLowerCase() === __filename.toLowerCase();
if(_invokedDirectly){
  if(process.argv.includes('--json')){
    // 只读输出健康 JSON；--strict 时以 exit_code 退出（便于脚本门禁）
    getHealthStatus({ alert: false, audit: false })
      .then(s => {
        console.log(JSON.stringify(s, null, 2));
        if(process.argv.includes('--strict') && s.exit_code) process.exitCode = s.exit_code;
      })
      .catch(e => { console.log(`[hidden_watchdog] json error: ${e.message}`); process.exitCode = 1; });
  } else if(process.argv.includes('--serve')){
    const idx = process.argv.indexOf('--serve');
    const port = parseInt(process.argv[idx + 1], 10) || parseInt(process.env.WATCHDOG_PORT || '8787', 10);
    serve(port).catch(e => { console.log(`[hidden_watchdog] serve error: ${e.message}`); process.exitCode = 1; });
  } else {
    main().catch(e => {
      console.log(`[hidden_watchdog] error: ${e.message}`);
      episodic('hidden_watchdog_error', { error: String(e && e.message || e) });
    });
  }
}