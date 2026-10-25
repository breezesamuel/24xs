# Tool Station Server — Pro tier (pairs with tool-station-starter)

Production checkout server for the starter kit's paywall. Deploy to Vercel (free tier OK, <=12 functions)
or any Node host.

## What's inside
- api/alipay.js — the gateway router: /api/pay (Alipay RSA2 page-pay, auto-redirect cashier form),
  /api/notify (signature-verified async callback), /api/order (idempotent authoritative query),
  /api/entitle (cross-device entitlements by referral code), /api/arcade (server-authoritative
  minute billing with invite bonuses), subscription/WeChat-Pay-Native/Stripe routes
- api/arcade-extra.js — leaderboard / feedback / alert endpoints
- lib/ — subscription wall, commission ladder, Stripe session/webhook, morning-youth product router
- lib/_lib/ — mailer, paypal orders, pending-order registry, plan catalog
- paid.html — return_url landing that confirms and unlocks
- vercel.json — routing table (all legacy URLs preserved)

## Environment variables (set these, no secrets in code)
ALIPAY_APP_ID / ALIPAY_MERCHANT_PRIVATE_KEY / ALIPAY_ALIPAY_PUBLIC_KEY
WECHAT_MCHID / WECHAT_APPID / WECHAT_CERT_SERIAL / WECHAT_PRIVATE_KEY (base64 of PEM) / WECHAT_APIV3_KEY
PAYPAL_CLIENT_ID / PAYPAL_SECRET / PAYPAL_ENV=live
KV_REST_API_URL / KV_REST_API_TOKEN (Upstash; orders survive restarts)
SMTP_* (receipts)

## Self-check endpoints (after deploy)
GET /api/health  — env presence matrix
GET /api/aliq    — signs a real Alipay query (TRADE_NOT_EXIST = signature accepted)
GET /api/verify  — creates a real 0.01 cashier order (cashier:true = rail live)

Honest note: Chinese payment rails require merchant qualification on your side; the code is
fail-closed — missing keys return explicit errors, never fake success.
