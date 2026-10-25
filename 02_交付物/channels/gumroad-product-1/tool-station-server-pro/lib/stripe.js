'use strict';
// stripe.js - Stripe Checkout 会话创建与 Webhook 验签
// 原则: fail-closed(缺密钥直接报错)、幂等(按 out_trade_no 去重)、服务端权威(仅信任 Stripe 事件)

const crypto = require('crypto');

function get(k) { return process.env[k] || ''; }

const SUB_PLANS = {
  trial: { cny: 1, usd: 1, days: 7, trial: true },
  pro:   { cny: 9.9, usd: 1.4, days: 31 },
  pro3:  { cny: 26, usd: 3.6, days: 93 },
  proY:  { cny: 99, usd: 13.8, days: 366 },
  team:  { cny: 299, usd: 41.5, days: 366 },
};

// 价格 ID 映射（需在 Stripe Dashboard 创建后填入环境变量）
// 格式: STRIPE_PRICE_TRIAL=price_xxx, STRIPE_PRICE_PRO=price_xxx ...
function getPriceId(plan) {
  const envKey = 'STRIPE_PRICE_' + plan.toUpperCase();
  return get(envKey);
}

async function createCheckoutSession(base, plan, ref, slug, inv, outTradeNo) {
  const sp = SUB_PLANS[plan];
  if (!sp) return { error: 'unknown_plan' };
  const priceId = getPriceId(plan);
  if (!priceId) return { error: 'stripe_price_not_configured', plan };

  const secretKey = get('STRIPE_SECRET_KEY');
  if (!secretKey) return { error: 'stripe_secret_key_missing' };

  // 动态导入 Stripe（Vercel 有内置 node_modules）
  let Stripe;
  try { Stripe = require('stripe'); } catch (e) { return { error: 'stripe_sdk_missing' }; }
  const stripe = Stripe(secretKey, { apiVersion: '2024-06-20' });

  const successUrl = base + '/paid.html?session_id={CHECKOUT_SESSION_ID}&ref=' + encodeURIComponent(ref);
  const cancelUrl = base + '/subwall.html?canceled=1';

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'payment',
      payment_method_types: ['card'],
      line_items: [{
        price: priceId,
        quantity: 1,
      }],
      success_url: successUrl,
      cancel_url: cancelUrl,
      client_reference_id: ref,
      metadata: {
        out_trade_no: outTradeNo,
        plan: plan,
        slug: slug,
        ref: ref,
        inv: inv,
        kind: 'sub',
      },
      payment_intent_data: {
        metadata: {
          out_trade_no: outTradeNo,
          plan: plan,
          ref: ref,
        },
      },
      allow_promotion_codes: true,
      billing_address_collection: 'auto',
      locale: 'auto',
    });
    return { ok: true, sessionId: session.id, url: session.url };
  } catch (e) {
    return { error: e.message };
  }
}

async function verifyWebhook(rawBody, signature) {
  const webhookSecret = get('STRIPE_WEBHOOK_SECRET');
  if (!webhookSecret) return { ok: false, error: 'stripe_webhook_secret_missing' };
  let Stripe;
  try { Stripe = require('stripe'); } catch (e) { return { ok: false, error: 'stripe_sdk_missing' }; }
  const stripe = Stripe(get('STRIPE_SECRET_KEY'), { apiVersion: '2024-06-20' });
  let event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, signature, webhookSecret);
  } catch (e) {
    return { ok: false, error: 'webhook_signature_verification_failed: ' + e.message };
  }
  return { ok: true, event };
}

// 处理 Stripe 支付成功事件
async function handlePaymentSuccess(event, saveOrderFn, activateSubFn, recordCommissionFn) {
  const session = event.data.object;
  const meta = session.metadata || {};
  const outTradeNo = meta.out_trade_no;
  const plan = meta.plan;
  const ref = meta.ref;
  const inv = meta.inv;
  const slug = meta.slug;
  const kind = meta.kind || 'sub';

  if (!outTradeNo || !plan || !ref) {
    return { ok: false, error: 'missing_metadata' };
  }

  // 金额（以分为单位转元/美元）
  const amountTotal = session.amount_total / 100;
  const currency = session.currency; // 'usd' 或 'cny'

  // 幂等：检查是否已处理
  // 注意：实际去重由 saveOrderFn 内部的 upsert 保证
  await saveOrderFn({
    out_trade_no: outTradeNo,
    slug: slug,
    ref: ref,
    invited_by: inv,
    plan: plan,
    kind: kind,
    list_price: String(amountTotal),
    pct: 0,
    amount: String(amountTotal),
    status: 'paid',
    paid_at: new Date().toISOString(),
    trade_no: session.payment_intent,
    trade_status: 'succeeded',
    currency: currency,
  });

  // 激活订阅
  if (kind === 'sub' && ref) {
    try {
      await activateSubFn(ref, plan, { out_trade_no: outTradeNo });
    } catch (e) {
      // 记录错误但不阻塞
      console.error('subwall activate failed:', e);
    }
  }

  // 分佣
  if (inv && inv !== ref) {
    try {
      await recordCommissionFn(inv, { out_trade_no: outTradeNo, amount: amountTotal, plan: plan, kind: kind });
    } catch (e) {
      console.error('commission record failed:', e);
    }
  }

  return { ok: true, out_trade_no: outTradeNo };
}

module.exports = {
  createCheckoutSession,
  verifyWebhook,
  handlePaymentSuccess,
  SUB_PLANS,
};