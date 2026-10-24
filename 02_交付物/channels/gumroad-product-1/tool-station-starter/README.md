# AI Micro-Tool Station Starter — build your own 5,000-page tool & game site

> The exact generator stack that powers a live site with **5,775 calculators/tools + 5,305 HTML5 games**,
> a shared paywall (10 free uses → monthly/buyout), referral cashback ladder, five-language UI
> (EN/中文/FR/DE/AR with RTL), server-authoritative minute billing for games, and one-file payment
> gateway wiring (Alipay page-pay + WeChat Native QR + PayPal).

## What's inside

```
generators/
  batch-app-generator.js   — scaffold a new calculator/tool page from a tiny spec
  arcade-build.js          — mass-produce HTML5 game pages (topics × modes × levels)
  arcade-engines.js        — the game engine library (anagram, math, word, balance, …)
  arcade-runtime.js        — per-minute billing runtime + invite bonuses
  arcade-topics.js         — topic/level data feeding the generator
shared/
  bds-core.js              — THE shared runtime: paywall, referral ladder, i18n(5 langs),
                             PDF export, analytics hooks, payment method chooser (Alipay/WeChat),
                             WeChat QR + auto-unlock polling, IndexNow-friendly markup helpers
docs/
  example-tool-page.html   — a real production tool page (airline layover calculator)
  example-pricing.html     — real pricing page with 5-language switcher
```

## Quickstart (3 commands)

```bash
# 1) generate a new tool page (edit the spec table at the top of the file)
node generators/batch-app-generator.js

# 2) build a batch of games (edit topics/levels in arcade-topics.js)
node generators/arcade-build.js

# 3) drop shared/bds-core.js next to your pages — paywall + i18n + payments are live
```

Point `bds-core.js`'s payment chooser at your own endpoints (one function: `bdsPayGo`),
or keep the default `/api/pay` contract — a ready-made server implementation ships with
the Pro tier (Alipay RSA2 signing, WeChat Pay v3 with cert auth, PayPal orders, order
store on Supabase/Upstash, idempotent query + webhook verify).

## Who is this for
- Indie makers who want a content-moat site (SEO: 10k+ indexable pages) with real checkout
- Agencies white-labeling tool/game portals for clients
- Anyone teaching "how to build a micro-SaaS content site" who wants a working reference

## License
Single commercial license: use it, modify it, ship it in unlimited projects of your own.
No resale of the kit itself.
