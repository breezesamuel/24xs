# Medium 草稿（英文，引流主站 + agents API）

## Title: I Built an 11,000-Page Tool Website That Charges Per Use — Here's the Entire Stack

**Subtitle**: 5,775 calculators, 5,305 playable games, five languages, Alipay/WeChat/PayPal —
with one shared runtime and zero frameworks.

**Body（骨架，发布前补真实数据与截图）**:

Most "programmatic SEO" sites are 10,000 pages of filler text. I wanted the opposite:
every page does something. Here's the architecture that made 11,000 *working* pages
maintainable by one person (and a few cron jobs).

**1. One shared runtime, thousands of thin pages.**
Every page ships ~60KB of the same `bds-core.js`: a 10-free-uses paywall, a referral
cashback ladder (1 friend = 10% back, up to 70%), a five-language dictionary
(EN/中文/FR/DE/AR with RTL), PDF export, and analytics hooks. Pages stay tiny;
the brain stays in one file.

**2. Generators, not authors.**
Two Node scripts produce the content: one turns tiny specs into calculator pages
(inputs → formula → result), the other combines topics × modes × levels into playable
HTML5 games with per-minute server billing. New vertical = one data file.

**3. Payments that actually worked on the third try.**
The Chinese rails are brutal: RSA2 signing, cert serials, AES business payloads,
signature errors that don't tell you which side is wrong. My hard-won checklist:
verify your private key against the gateway with a read-only API before shipping
(`40004 TRADE_NOT_EXIST` means your signature is *accepted*), fingerprint every key
by its JWK modulus, and never trust client-reported balances — the server counts
minutes itself.

**4. The entitlement graph.**
Orders live in a KV store keyed by an anonymous referral code in localStorage.
Pay once on your laptop, the unlock follows you to your phone. Referrals discount
the payer, not the referred — paying it *forward* converts 3× better in our data.

**5. What I'd do differently.**
IndexNow from day one (11,313 URLs accepted in three batches). Chrome extension
as a distribution channel (the store has its own search traffic). And a health
endpoint that probes your *own* payment rails every 15 minutes — we caught a
signature mismatch only because a watchdog refused to stay quiet.

Try it: [tools.highkingflower.com](https://tools.highkingflower.com) ·
The agents API behind it: [bingdashanai.highkingflower.com/agents](https://bingdashanai.highkingflower.com/agents)
(5 deterministic agents, JSON in/out, x402 or subscription).

*Tags*: programming, saas, indie-hacking, seo, payments
