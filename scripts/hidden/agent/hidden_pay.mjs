#!/usr/bin/env node
/**
 * hidden_pay.mjs — 支付网关抽象层（多网关：支付宝 / MoltsPay / x402）
 *
 * 【设计原则】
 *   fail-closed：无凭据时明确记录"未配置"并拒绝，绝不假装收款成功。
 *   非破坏性：只写 autoops/hidden/payments_auto.jsonl（auto:true），
 *             绝不触碰 11_数据资产/registry_real_verified/*。
 *
 * 【赚钱闭环】
 *   CRM won → createPayment 生成支付意图 → 客户支付 → 网关回调 webhook
 *   → verifyCallback 验签 → confirmOrder 确认订单 → OMS 推进发货
 *
 * 【网关凭据（环境变量）】
 *   alipay:   ALIPAY_APP_ID, ALIPAY_PRIVATE_KEY, ALIPAY_PUBLIC_KEY
 *   moltspay: MOLTSPAY_WEBHOOK_SECRET, MOLTSPAY_API_KEY
 *   x402:     X402_SECRET, X402_WALLET
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import crypto from 'crypto';
import { episodic, fact } from '../brain/hidden_brain.mjs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '../../../');
const H = path.join(ROOT, 'autoops/hidden');
const PAY = path.join(H, 'payments_auto.jsonl');
const ORD = path.join(H, 'orders_auto.jsonl');

const GATEWAY_ENV = {
  alipay:   ['ALIPAY_APP_ID', 'ALIPAY_PRIVATE_KEY', 'ALIPAY_PUBLIC_KEY'],
  moltspay: ['MOLTSPAY_WEBHOOK_SECRET', 'MOLTSPAY_API_KEY'],
  x402:     ['X402_SECRET', 'X402_WALLET'],
};

function load(p){ if(!fs.existsSync(p)) return []; return fs.readFileSync(p,'utf8').trim().split('\n').map(l=>{try{return JSON.parse(l)}catch(e){return null}}).filter(Boolean); }
function append(p,o){ fs.appendFileSync(p, JSON.stringify(o)+'\n'); }
function save(p,arr){ fs.writeFileSync(p, arr.map(x=>JSON.stringify(x)).join('\n')+(arr.length?'\n':'')); }
function now(){ return new Date().toISOString(); }
function h(s){ return crypto.createHash('sha256').update(String(s)).digest('hex').slice(0,14); }

/** 网关配置状态（只报告缺失项，不打印任何密钥值） */
export function gatewayStatus(method){
  const required = GATEWAY_ENV[method] || [];
  const missing = required.filter(v => !process.env[v]);
  return { method, configured: missing.length === 0, missing };
}

export function allGatewaysStatus(){
  return Object.keys(GATEWAY_ENV).map(gatewayStatus);
}

/**
 * 创建支付意图。
 * 无凭据 → status:'unconfigured'（fail-closed，不假装成功）。
 * 有凭据 → status:'created' + payment_url（真实网关跳转链接）。
 */
export async function createPayment({ order_id, amount, currency = 'CNY', method = 'alipay', subject = '' }){
  if(!fs.existsSync(H)) fs.mkdirSync(H, { recursive: true });
  const st = gatewayStatus(method);
  const rec = {
    payment_id: `PAY-${Date.now()}-${h(order_id + method)}`,
    order_id, amount: Number(amount), currency, method, subject,
    status: 'pending', auto: true,
    created_at: now(),
  };

  if(!st.configured){
    rec.status = 'unconfigured';
    rec.error = `gateway ${method} not configured (missing env: ${st.missing.join(', ')})`;
    append(PAY, rec);
    episodic('hidden_pay_unconfigured', { payment_id: rec.payment_id, method, missing: st.missing });
    return { ok: false, ...rec };
  }

  rec.status = 'created';
  rec.payment_url = buildPaymentUrl(method, rec);
  rec.expires_at = new Date(Date.now() + 30 * 60 * 1000).toISOString(); // 30 分钟有效
  append(PAY, rec);
  episodic('hidden_pay_created', { payment_id: rec.payment_id, method, amount: rec.amount, order_id });
  return { ok: true, ...rec };
}

function buildPaymentUrl(method, pay){
  if(method === 'alipay'){
    // 真实支付宝网关由 10_官网/api/alipay_pay.py 生成；这里只记录意图
    return `alipay://pay/${pay.payment_id}?amount=${pay.amount}&order=${encodeURIComponent(pay.order_id)}`;
  }
  if(method === 'moltspay'){
    return `https://app.moltspay.com/pay/${pay.payment_id}`;
  }
  if(method === 'x402'){
    return `x402://pay/${pay.payment_id}?amount=${pay.amount}`;
  }
  return '';
}

/**
 * 验证支付回调（fail-closed：无凭据一律无效）。
 * 返回 { valid, order_id?, amount?, reason? }
 */
export function verifyCallback(method, payload, signature){
  const st = gatewayStatus(method);
  if(!st.configured){
    return { valid: false, reason: `gateway ${method} unconfigured (missing: ${st.missing.join(', ')})` };
  }
  try{
    if(method === 'alipay')   return verifyAlipay(payload, signature);
    if(method === 'moltspay') return verifyMoltspay(payload, signature);
    if(method === 'x402')     return verifyX402(payload, signature);
    return { valid: false, reason: 'unknown gateway' };
  }catch(e){
    return { valid: false, reason: `verify error: ${e.message}` };
  }
}

/* ---- 支付宝 RSA2 验签（真实实现，凭据齐全时生效） ---- */
function verifyAlipay(payload, signature){
  const priv = process.env.ALIPAY_PRIVATE_KEY || '';
  const pub  = process.env.ALIPAY_PUBLIC_KEY  || '';
  // 支付宝回调：用支付宝公钥验签 sign
  const signStr = canonicalQueryString(payload);
  const ok = rsaVerify(signStr, signature, pub);
  return ok
    ? { valid: true, order_id: payload.out_trade_no || payload.outTradeNo, amount: parseFloat(payload.total_amount || payload.totalAmount) }
    : { valid: false, reason: 'alipay signature mismatch' };
}

/* ---- MoltsPay HMAC 验签 ---- */
function verifyMoltspay(payload, signature){
  const secret = process.env.MOLTSPAY_WEBHOOK_SECRET || '';
  const body = typeof payload === 'string' ? payload : JSON.stringify(payload);
  const expect = crypto.createHmac('sha256', secret).update(body).digest('hex');
  const ok = timingSafeEqual(expect, String(signature || ''));
  return ok
    ? { valid: true, order_id: payload.order_id || payload.orderId, amount: parseFloat(payload.amount) }
    : { valid: false, reason: 'moltspay hmac mismatch' };
}

/* ---- x402 验签 ---- */
function verifyX402(payload, signature){
  const secret = process.env.X402_SECRET || '';
  const body = typeof payload === 'string' ? payload : JSON.stringify(payload);
  const expect = crypto.createHmac('sha256', secret).update(body).digest('hex');
  const ok = timingSafeEqual(expect, String(signature || ''));
  return ok
    ? { valid: true, order_id: payload.order_id, amount: parseFloat(payload.amount) }
    : { valid: false, reason: 'x402 hmac mismatch' };
}

function rsaVerify(data, signature, publicKeyPem){
  try{
    const verifier = crypto.createVerify('RSA-SHA256');
    verifier.update(data);
    verifier.end();
    return verifier.verify(publicKeyPem, signature, 'base64');
  }catch(e){ return false; }
}

function timingSafeEqual(a, b){
  const ba = Buffer.from(a); const bb = Buffer.from(b);
  if(ba.length !== bb.length) return false;
  return crypto.timingSafeEqual(ba, bb);
}

/** 支付宝回调规范化的待签名字符串（按 key 排序，去掉 sign/sign_type） */
function canonicalQueryString(params){
  return Object.keys(params)
    .filter(k => k !== 'sign' && k !== 'sign_type' && params[k] !== '')
    .sort()
    .map(k => `${k}=${params[k]}`)
    .join('&');
}

/**
 * 支付成功后确认订单：把订单从 pending 推进到 processing（待发货）。
 * 由 webhook 调用，验签通过后才执行。
 */
export function confirmOrder(paymentId, verifyResult){
  const pays = load(PAY);
  const pay = pays.find(p => p.payment_id === paymentId);
  if(!pay) return { ok: false, reason: 'payment not found' };
  if(pay.status === 'paid') return { ok: true, already: true, order_id: pay.order_id };

  pay.status = 'paid';
  pay.paid_at = now();
  pay.verified = verifyResult;
  save(PAY, pays);
  fact(`payment_paid_${pay.payment_id}`, { order_id: pay.order_id, amount: pay.amount, method: pay.method }, 'hidden_pay');
  episodic('hidden_pay_paid', { payment_id: pay.payment_id, order_id: pay.order_id, amount: pay.amount });

  // 推进对应订单到 processing
  const orders = load(ORD);
  let advanced = false;
  for(const o of orders){
    if((o.order_id === pay.order_id || o.payment_id === pay.payment_id) && o.status === 'pending'){
      o.status = 'processing';
      o.paid_at = pay.paid_at;
      o.timeline = o.timeline || [];
      o.timeline.push({ ts: now(), act: 'auto_paid', method: pay.method });
      o.updated_at = now();
      advanced = true;
    }
  }
  if(advanced) save(ORD, orders);
  return { ok: true, order_id: pay.order_id, amount: pay.amount, advanced };
}

/** CLI：报告所有网关配置状态（不打印密钥值） */
if(process.argv[1] && process.argv[1].endsWith('hidden_pay.mjs')){
  const st = allGatewaysStatus();
  console.log('[hidden_pay] gateway config status:');
  for(const g of st){
    console.log(`  ${g.method.padEnd(9)} ${g.configured ? 'CONFIGURED' : 'NOT CONFIGURED (missing: ' + g.missing.join(', ') + ')'}`);
  }
  const pays = load(PAY);
  console.log(`[hidden_pay] total payment records: ${pays.length}`);
}
