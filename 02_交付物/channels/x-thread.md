# X Building in Public Thread（英文，9 条推文）

## Tweet 1（Hook）
I built a website with 17,481 pages and 15 revenue-generating products in 7 days. One person. One AI assistant. Zero ad spend.

Here's exactly how (and what I learned):

🧵

## Tweet 2（Problem）
The problem: Chinese SMBs need web tools (calculators, converters, checkers) but can't afford custom development. Existing solutions are either too expensive or too generic.

So I asked: what if ONE system could generate thousands of targeted tool pages automatically?

## Tweet 3（Solution）
I built a "tool factory":

→ Template engine generates tool pages from data specs
→ Each page targets a specific long-tail search query
→ Shared runtime handles i18n (5 languages), paywall, viral sharing
→ Deployed on Vercel free tier

Result: 5,775 tools + 5,305 games in one deploy.

## Tweet 4（Tech stack）
The entire stack:

• Frontend: Pure HTML/CSS/JS (no framework)
• Backend: Node.js API routes on Vercel
• Payments: Alipay RSA2 + WeChat Pay v3 + PayPal
• Database: Upstash Redis (serverless)
• Search: IndexNow API (instant Bing indexing)
• Viral loop: Every user = a distribution node

All in 17,481 pages. All indexed.

## Tweet 5（The hard part）
The hardest part wasn't the code.

It was Chinese payment integration:
→ Alipay RSA2 signing (cryptographic, 1-shot)
→ WeChat Pay v3 (certificate auth, platform serial numbers)
→ PayPal (order + capture + subscription)

Each took days to debug. The signing errors don't tell you WHICH side is wrong.

My tip: verify with a read-only API first. If you get "TRADE_NOT_EXIST" (not "INVALID_SIGNATURE"), your key is accepted.

## Tweet 6（Revenue model）
Revenue model: freemium + BYOK

→ 10 free uses per tool
→ Then ¥9.9 unlock (or subscribe ¥10+/month)
→ Referral ladder: 1 friend = 10% back, 5 = 70%, 10 = free forever
→ Viral loop: every free user sees a share button after each result
→ BYOK AI chat: users bring their own API keys, zero compute cost

## Tweet 7（Current status）
Current status:

✅ 17,481 pages live and indexed
✅ 5 payment channels verified with real orders
✅ 15 revenue-generating products
✅ 24/7 automated systems (crawling, scanning, auditing)
✅ 3 open-source repos on GitHub

⬜ First paying customer

## Tweet 8（What I'd do differently）
What I'd do differently:

1. Start with 100 pages, not 17,000 (validate before scaling)
2. Build the viral loop BEFORE launching
3. Pick ONE niche and dominate it
4. Charge from day 1 (even ¥1)

The biggest mistake: building everything before talking to a single user.

## Tweet 9（What's next）
Next: sharing the full playbook — every bug, every workaround, every lesson.

Follow if you're building in the China market or interested in programmatic SEO + payments.

Links:
🔗 Live site: tools.highkingflower.com
🔗 AI tools: bingdashanai.highkingflower.com/agents
🔗 Open source: github.com/breezesamuel

---

## 中文版（发微博/知乎/公众号）

**标题**：7 天从零搭建 17,481 页网站的完整复盘

**正文**：
一个 AI 助手，7 天，17,481 页网页，15 个可收费产品，5 条收款通道（支付宝/微信/PayPal/x402），全部实测通过。

关键技术决策：
- 纯 HTML/CSS/JS（不用框架，部署零依赖）
- 共享运行时（一个 bds-core.js 管所有页面的付费墙/多语言/推荐系统）
- 模板+数据驱动（不是手写页面，是生成器批量产出）
- IndexNow API（提交搜索引擎即时收录，不等爬虫）
- 病毒循环（每个免费用户=分发节点，结果页自动出现分享条）

最难的部分不是代码——是中国支付集成：
- 支付宝 RSA2 签名（一次通过率 0%，调试 3 天）
- 微信支付 v3 证书认证（序列号+平台证书+APIv3 密钥三件套）
- PayPal（最简单的，但退款/争议处理复杂）

最大的教训：**先找到 1 个用户再建 17,000 页。** 我先建了页面再找人——顺序反了。

**体验地址**：tools.highkingflower.com
**AI 工具**：bingdashanai.highkingflower.com/agents
**开源代码**：github.com/breezesamuel/micro-tool-factory
