/**
 * api/internal/hidden/webhook.js — 支付回调接收端点
 *
 * 接收支付宝 / MoltsPay / x402 的支付成功通知。
 * fail-closed：未配置网关或验签失败一律拒绝，绝不确认未到账订单。
 *
 * 路由：POST /api/internal/hidden/webhook?gateway=alipay|moltspay|x402
 *
 * 安全：
 *   - 只接受 POST
 *   - 验签通过才确认订单
 *   - 幂等：同一 payment_id 重复回调只确认一次
 */
const path = require('path');
const { fileURLToPath } = require('url');
const { spawn } = require('child_process');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../../../');

const ALLOWED_GATEWAYS = ['alipay', 'moltspay', 'x402'];

function getHeader(req, name){
  return req.headers[name.toLowerCase()] || '';
}

function readBody(req){
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', c => {
      body += c;
      if(body.length > 1e6){ req.destroy(); reject(new Error('body too large')); }
    });
    req.on('end', () => resolve(body));
    req.on('error', reject);
  });
}

/** 调用 hidden_pay.mjs 的验签与确认逻辑（子进程隔离，避免在 serverless 内引入 ESM） */
function runPay(args){
  return new Promise(resolve => {
    const p = spawn('node', [path.join(ROOT, 'scripts/hidden/agent/hidden_pay.mjs'), ...args], {
      cwd: ROOT,
      env: process.env,
    });
    let out = '', err = '';
    p.stdout.on('data', d => out += d);
    p.stderr.on('data', d => err += d);
    p.on('close', code => resolve({ code, out, err }));
    p.on('error', e => resolve({ code: 1, out: '', err: e.message }));
  });
}

module.exports = async function handler(req, res){
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Cache-Control', 'no-store');

  if(req.method !== 'POST'){
    return res.status(405).json({ ok: false, error: 'method not allowed, POST only' });
  }

  const url = new URL(req.url, 'http://localhost');
  const gateway = (url.searchParams.get('gateway') || '').toLowerCase();

  if(!ALLOWED_GATEWAYS.includes(gateway)){
    return res.status(400).json({ ok: false, error: `unknown gateway '${gateway}' (allowed: ${ALLOWED_GATEWAYS.join(', ')})` });
  }

  let raw;
  try{
    raw = await readBody(req);
  }catch(e){
    return res.status(400).json({ ok: false, error: 'bad request body' });
  }

  let payload;
  try{
    payload = JSON.parse(raw);
  }catch(e){
    payload = raw; // 支付宝回调可能是表单编码，按字符串处理
  }

  // 签名：网关通常放在 header 或 body
  const signature =
    getHeader(req, 'x-sign') ||
    getHeader(req, 'x-signature') ||
    getHeader(req, 'x-moltspay-signature') ||
    (payload && typeof payload === 'object' ? (payload.sign || payload.signature || '') : '');

  // fail-closed：调用支付模块验签 + 确认订单
  const input = JSON.stringify({ gateway, payload, signature });
  const result = await runPay(['--verify', gateway, input]);

  let verdict;
  try{
    verdict = JSON.parse(result.out);
  }catch(e){
    verdict = { ok: false, error: 'pay module error', detail: result.err };
  }

  if(verdict && verdict.ok){
    return res.status(200).json({ ok: true, gateway, confirmed: true, order_id: verdict.order_id, amount: verdict.amount });
  }

  // 验签失败 / 未配置：拒绝确认（403），但记录日志便于排查
  console.log('[webhook] rejected', JSON.stringify({ gateway, reason: verdict?.reason || verdict?.error, ts: new Date().toISOString() }));
  return res.status(403).json({ ok: false, gateway, confirmed: false, reason: verdict?.reason || verdict?.error || 'verification failed' });
};

module.exports.config = {
  runtime: 'nodejs',
  maxDuration: 30
};
