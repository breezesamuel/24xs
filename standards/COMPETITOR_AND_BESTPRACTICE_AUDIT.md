# COMPETITOR & BEST-PRACTICE AUDIT (查缺补漏)

**Audience:** AI Arcade (https://tools.highkingflower.com/arcade) + AutoOps pipeline operators
**Date:** 2026-10-12
**Method:** web search + direct fetch of vendor docs and GitHub repo pages. Star counts pulled from the public shields.io badges (`img.shields.io/github/stars/...`) on 2026-10-12, so they are *current*, not projected. Licenses cross-checked against project LICENSE pages / official docs; anything I could not confirm is tagged **UNVERIFIED**.
**Relationship to existing work:** This audit deliberately *complements* `standards/WHEEL_SELECTION_SOP.md` (5-dimension wheel scoring, permissive-license red lines, GitHub-API anti-hallucination probe). It does **not** re-derive that SOP; it adds the checks the SOP does not yet do (vulnerability scanning, archived-state, security posture) and market/competitor facts.

**No fabrication rule applied:** every tool/repo below has a URL that I fetched or that appeared in a fetched source. Repos that could not be verified are excluded or marked.

---

## PART 1 — COMPETITORS (查缺补漏)

### 1(a) AI mini-game / pay-per-play arcade (CN + global)

| Name | URL | What it does | Pricing model | What we can steal | Our gap |
|---|---|---|---|---|---|
| **Astrocade** | https://www.astrocade.com/ | "Social gaming platform where anyone can build, share, and play AI games"; endless feed of short games, AI maker, no download. Reported 10M monthly users (Reddit r/aigamedev). | **Free**; creator payouts mentioned; no listed paid tier | **Social feed + remix loop** (play→remix→share) is the growth engine. Feed-first discovery beats an invite-gated menu. | We are invite-link gated with no public feed/remix; acquisition is manual. Add a public "trending games" feed + one-tap remix to drive organic viral loop. |
| **Rosebud AI Game Maker** | https://rosebud.ai/ | Prompt→playable 2D/3D/voxel browser game; code download + Windows export on higher tiers. | Freemium credits (Free = 8,000 credits, weekly refill in eligible regions; paid tiers "Indie Dev/10x Dev/Scale" — exact price in-app) | **Credit/turn-based metering** of AI work (build, edit, image, music). Transparent "what each turn cost". | Our "play-time/balance" is time-based only; no cost-transparency per AI generation. Show per-play credit burn. |
| **Plutus: AI Game Maker** | https://play.google.com/store/apps/details?id=com.karata.unicohub | Mobile AI game maker + "endless arcade" + **skill-based tournaments**. | Free app; monetization via tournaments/IAP (details **UNVERIFIED**) | **Tournaments / skill-based competitions** as retention + monetization. | No competitive/leaderboard layer in our arcade. Add weekly skill tournaments (entry from balance). |
| **Websim** | https://websim.com/ | Free prompt-to-web sandbox; community makes small browser games/simulations, each with a shareable, for­kable URL. | Free | **Forkable share URLs** for every generated game; zero-friction sharing. | Generated games likely lack public, forkable permalinks. Add `/g/{id}` share + fork. |
| **Aippy – AI Game Maker** | https://play.google.com/store/apps/details?id=com.nadaai.aippy | "完全免费的 AI 游戏制作工具… 没有付费墙，没有广告", instant interactive experiences. | Free | Positioning as genuinely free; removes friction vs pay-per-play. | Our pay-per-play pricing needs a strong value story vs free rivals → emphasize curated/curated multiplayer/leaderboard value, not raw generation. |
| **百度秒哒 (Miaoda)** | https://cloud.baidu.com/doc/MIAODA/s/Sm88db6er | Baidu no-code generative app platform; generates websites, mini-programs, H5, **小游戏** from natural language (3.0 launched May 2026). | Free / enterprise tiers (exact pricing **UNVERIFIED**) | **国内合规发布链路** (备案/小程序生态) bundled with generation. | We generate/operate outside the WeChat/Douyin mini-game distribution rails; CN distribution + 备案 is our biggest market gap. |
| **微信小游戏 ecosystem** | https://developers.weixin.qq.com/minigame/dev/guide/ | Dominant CN mini-game platform: 500M+ MAU; IAA (ads) + IAP (in-app purchase); iOS IAP added with 15% platform cut. | Platform rev-share (IAA/IAP); iOS 15% | **Mixed monetization (IAA+IAP)** and platform account/pay/social rails. | Pay-per-play via own Alipay link skips the platform's social distribution and trust. Consider a WeChat/Douyin mini-game build as a top-of-funnel. |
| **抖音小游戏** | https://developer.open-douyin.com/ | ByteDance mini-game ecosystem; 2025 active scale +120% YoY; short-video↔game loop. | IAA/IAP, dev subsidies | **Short-video → game** conversion loop; creator/达人 content. | No short-video distribution; content官 output should feed short-video channels, not just text. |
| **Poki** | https://developers.poki.com/ | Largest free web-game portal (HTML5, no download). | 50/50 lifetime ad revenue share (per Hology) | **Ad rev-share** as an *additional* revenue stream alongside pay-per-play. | Our arcade is pay-only; adding rewarded ads can monetize non-paying invitees. |
| **CrazyGames** | https://developer.crazygames.com/ | Browser-game portal + SDK; monetization via ads. | Rev-share determined by factors (not public) | **One-time SDK integration** for ads/analytics; mature developer portal. | No ad SDK / analytics contract; consider CrazyGames/Poki publishing for reach. |
| **Apple Arcade** | https://www.apple.com/apple-arcade/ | Curated subscription catalog (not AI-generated specifically). | Subscription (monthly, family) | **Curated catalog quality bar** + family sharing. | Subscription tier could complement per-play balance (e.g., day pass). |

**Strategic read:** the AI-game field monetizes by **free + ads/creator-payout**, or **subscription** — *nobody* at scale does pure pay-per-play-by-time. That is our differentiation **and** our compliance/UX risk (China: game 版号/备案 + 未成年人保护 apply to paid games). Pay-per-play must be justified by curation, leaderboards, and multiplayer; and we should layer IAA (rewarded ads) + a pass/tournament SKU rather than relying on a single meter.

---

### 1(b) Open-source alternatives to our self-built modules (build-vs-buy)

Star/release data verified 2026-10-12 via shields.io GitHub badges. "Last release" wording is the badge's own relative date.

#### Crawler / ingest

| Project | URL | License | Stars | Last release | Viable build-vs-buy? |
|---|---|---|---|---|---|
| Crawl4AI | https://github.com/unclecode/crawl4ai | Apache-2.0 | 85k | v0.9.4 (Sep 2026) | **Yes — best fit.** Python, LLM-ready markdown, already ranked #3 in our SOP. Use as the ingest "wheel" instead of maintaining a bespoke Playwright crawler. |
| Firecrawl | https://github.com/firecrawl/firecrawl | AGPL-3.0 | 191k | v2.11.0 (Jun 2026) | **No for self-host** (AGPL red line per our SOP); cloud API acceptable only if we accept vendor lock. |
| Crawlee | https://github.com/apify/crawlee | Apache-2.0 | 26k | v3.18.2 (Sep 2026) | Optional if we want Node.js-native crawling; Apache-2.0 is clean. |
| trafilatura | https://github.com/adbar/trafilatura | Apache-2.0 | (SOP: 6,955) | — | Keep as the extraction library; SOP already marks it DIRECT_USE. |

#### Workflow orchestration

| Project | URL | License | Stars | Last release | Viable? |
|---|---|---|---|---|---|
| Prefect | https://github.com/PrefectHQ/prefect | Apache-2.0 | 24k | v3.8.8 (recent) | Viable, but heavy for our 15-stage cron; SOP already says SUITABLE-not-required. |
| Apache Airflow | https://github.com/apache/airflow | Apache-2.0 | 47k | v3.3.2 (Sep 2026) | Heavier ops; not needed. |
| Dagster | https://github.com/dagster-io/dagster | Apache-2.0 | 16k | v1.13.26 (recent) | Asset-oriented; overkill. Note: **reported Prefect acquisition of Dagster Labs (Jul 2026)** — watch governance (`prefect.io/prefect-acquires-dagster`). |
| Temporal | https://github.com/temporalio/temporal | MIT | 24k | v1.32.1 (recent) | Strong durable-execution engine; only worth it if workflows grow past cron. |
| n8n | https://github.com/n8n-io/n8n | **Sustainable Use License (fair-code, not OSI)** | 207k | n8n@2.42.6 (recent) | **Caution** — fair-code triggers our SOP "REVIEW"; free to self-host internally but not a permissive license for redistribution. |

**Verdict:** keep the self-built orchestrator + GitHub Actions/Vercel cron/PM2 (as SOP concludes). Do **not** adopt a heavyweight engine yet; revisit only if stage count/long-running jobs grow.

#### Payments

| Project | URL | License | Stars | Last release | Viable? |
|---|---|---|---|---|---|
| Hyperswitch (Juspay) | https://github.com/juspay/hyperswitch | Apache-2.0 | 45k | v1.127.0 (Sep 2026) | Viable if we ever need multi-acquirer routing; **no Alipay/WeChat native** — CN rails still via official SDKs. |
| Kill Bill | https://github.com/killbill/killbill | Apache-2.0 | 5.8k | killbill-0.24.22 (Sep 2026) | Subscription billing; Java stack mismatch with our Node/Python. |
| Lago | https://github.com/getlago/lago | AGPL-3.0 | 11k | v1.55.0 (recent) | **No** (AGPL red line). |

**Verdict:** for Alipay, use the **official Alipay SDK** and mirror the verification logic below; OSS orchestrators add little for a single-rail CN checkout.

#### CRM / OMS

| Project | URL | License | Stars | Last release | Viable? |
|---|---|---|---|---|---|
| Twenty | https://github.com/twentyhq/twenty | AGPL-3.0 (LICENSE file; package.json says GPL-3.0) | 58k | twenty/v2.45.0 (Oct 2026) | **No for a closed SaaS** (network-copyleft); fine internally with care. First-party MCP server is a nice pattern to copy. |
| EspoCRM | https://github.com/espocrm/espocrm | AGPL-3.0 | 3.5k | v10.0.9 (Sep 2026) | No for closed redistribution; lightweight CRM reference. |
| ERPNext / Frappe | https://github.com/frappe/erpnext | GPL-3.0 | 40k | v15.122.0 (recent) | **No** (GPL red line per SOP). |
| Medusa | https://github.com/medusajs/medusa | **MIT (core)** | 37k | v2.21.2 (Sep 2026) | **Yes — top备选.** MIT core, commerce/OMS primitives; SOP already names Medusa the preferred fallback. |
| Saleor | https://github.com/saleor/saleor | BSD-3-Clause | 23k | v3.23.41 (recent) | Viable (Python/GraphQL); heavier. |
| Vendure | https://github.com/vendure-ecommerce/vendure | **UNVERIFIED** (sources conflict: MIT vs GPLv3) | 8.5k | v3.7.4 (Oct 2026) | Do not adopt until the LICENSE file is read directly. |
| Ever Gauzy | https://github.com/ever-co/ever-gauzy | AGPL-3.0 | 8.3k | v111.48.2 (Oct 2026) | No for closed SaaS. |

**Verdict:** keep our自研 OMS/CRM (SOP: "重复造轮子" warning); Medusa is the only clean-license OMS candidate if we expand to multi-SKU.

#### Content generation

| Project | URL | License | Stars | Last release | Viable? |
|---|---|---|---|---|---|
| ComfyUI | https://github.com/comfyanonymous/ComfyUI | GPL-3.0 | 137k | v0.39.0 (Oct 2026) | **No** as an embedded component (GPL red line); OK as a **separate, independently-run service** invoked over API (SOP would still flag). |
| AUTOMATIC1111 SD WebUI | https://github.com/AUTOMATIC1111/stable-diffusion-webui | AGPL-3.0 | 165k | v1.10.1 (Feb 2025 — stale) | **No** (AGPL + stale). |

**Verdict:** generation should call hosted model APIs (which we already do) rather than embedding copyleft image stacks.

#### Self-evolving agent loops

| Project | URL | License | Stars | Last release | Viable? |
|---|---|---|---|---|---|
| OpenHands | https://github.com/All-Hands-AI/OpenHands | MIT | 91k | v1.26.0 (recent) | **Yes** — MIT, active; useful scaffolding for our `hidden_improver`/`hidden_planner`. |
| SWE-agent | https://github.com/SWE-agent/SWE-agent | MIT | 21k | v1.1.0 (May 2025 — staler) | Reference for agent loops; not actively updated as of mid-2025. |
| EvoAgentX | https://github.com/EvoAgentX/EvoAgentX | **UNVERIFIED** | 3.4k | v0.1.4 (Jun 2026) | Research-grade prompt/workflow self-evolution; verify license before use. |
| Awesome-Self-Evolving-Coding-Agents | https://github.com/iSEngLab/Awesome-Self-Evolving-Coding-Agents | (**UNVERIFIED**) | — | 2026 | Survey/list to mine patterns (AgentEvolver, EvolveR, OpenEvolve). Not production code. |

**Verdict:** our self-built `hidden_improver` loop is defensible; OpenHands (MIT) is the cleanest external reference to steal patterns from.

---

## PART 2 — OPTIMAL SOLUTIONS (全网最优化方案, 查缺补漏)

### 2.1 Anti-hallucination when the LLM recommends GitHub repos

**Industry best practice**
- **Existence:** resolve every recommendation through the GitHub REST API `GET /repos/{owner}/{repo}`; treat 404 as "does not exist" and 403 as rate-limit (retry with token). *(Already in our SOP: `standards/WHEEL_SELECTION_SOP.md`, steps 1–2.)*
- **Archived / staleness:** check the API `archived` field and `pushed_at`/`updated_at`; never adopt an archived repo. OpenSSF Scorecard has a dedicated `archived` probe and a `Maintained` metric — https://github.com/ossf/scorecard and https://deps.dev/project/github/ossf%2Fscorecard.
- **Independent metadata:** ecosyste.ms Repos API provides archived/last-commit/stars across 2k+ hosts — https://repos.ecosyste.ms/ and https://ecosyste.ms/api. deps.dev API gives dependency/security graph — https://docs.deps.dev/api/v3alpha/.
- **Vulnerabilities:** query **OSV.dev** by package+version and by commit (`POST https://api.osv.dev/v1/query`, docs https://google.github.io/osv.dev/), or run **OSV-Scanner** (Apache-2.0, 11k★) in CI — https://github.com/google/osv-scanner. Backup: GitHub Advisory Database via REST (`/advisories`) or GraphQL `securityAdvisories` — https://docs.github.com/en/rest/security-advisories/global-advisories and https://docs.github.com/en/graphql/reference/security-advisories.
- **Supply chain:** pin to a commit/tag and verify provenance (SLSA) before vendoring.

**Concrete gap / upgrade for us**
1. Our SOP stops at existence + license + freshness. **Add a mandatory security gate:** for each selected wheel, call OSV API (by repo→package mapping or commit) and reject on any unpatched HIGH/CRITICAL.
2. **Add the `archived` flag to D1** (currently only `pushed_at`): a repo can be "recently pushed" yet archived/read-only.
3. **Store provenance** (repo URL, resolved commit SHA, license SPDX, OSV result, scorecard score, timestamp) in `standards/reuse_candidates.yml` so an LLM can never silently re-introduce a rejected repo.
4. **Fail-closed:** if any verifier errors, the wheel is not auto-selected (human REVIEW), matching the SOP's `NOASSERTION` philosophy.

---

### 2.2 Fail-closed payment webhook verification

**Industry best practice**
- **Verify signatures first, then act.** Stripe: verify with the `Stripe-Signature` header + endpoint secret; without it attackers can forge fulfillment events — https://docs.stripe.com/webhooks.
- **Alipay:** remove `sign`/`sign_type`, sort remaining params, RSA2-verify; only trust `trade_status ∈ {TRADE_SUCCESS, TRADE_FINISHED}`; features include `notify_id` (通知校验 ID) and `out_trade_no`/`total_amount` — https://opendocs.alipay.com/open/194/103296 and self-verify guide https://opendocs.alipay.com/common/02mse7.
- **WeChat Pay APIv3:** build the verify string from `Wechatpay-Timestamp` + `Wechatpay-Nonce` + body, verify `Wechatpay-Signature` against the platform cert/public key, then **decrypt** the `AEAD_AES_256_GCM` payload; respond `200/204` only on success (otherwise WeChat keeps retrying) — https://pay.weixin.qq.com/doc/v3/merchant/4012647393.
- **Idempotency / replay:** persist the platform event id (`notify_id` / event `id`) in a unique table and process once; a production pattern is event-id dedupe + TTL (DynamoDB/Redis) and a DLQ on failure — https://theroadtoenterprise.com/blog/stripe-webhook-idempotency-production and the AWS DLQ pattern https://stripe.dev/blog/building-resilient-webhook-handlers-aws-dlqs-stripe-events.
- **Cross-check the order** (amount, currency, order id, seller/app id) against our DB before crediting; reconcile missed notifications by calling the platform's **order-query API** on a timer.

**Concrete gap / upgrade for us**
1. **Fail-closed gate:** credit balance **only** when `sign_ok AND out_trade_no exists AND amount == order.amount AND seller/app_id matches AND status == success`. Any failure → do not credit, log, and return the non-success response the platform expects.
2. **Replay/idempotency table** keyed on `notify_id` (Alipay) / event `id` (WeChat) with TTL; second delivery must be a no-op returning success.
3. **Reconciliation job** (already in our 15-stage loop family) that queries the payment gateway for `WAIT_BUYER_PAY`/pending orders and closes the gap if a webhook was lost; notify via the watchdog.
4. **Refund/chargeback handling** must also adjust balance idempotently.

---

### 2.3 Alert dedup + escalation + recovery for a watchdog

**Best practice**
- **Dedup/group/inhibit/silence** by stable labels via Prometheus Alertmanager; low-severity alerts are inhibited while a high-severity alert on the same target is active — https://prometheus.io/docs/alerting/latest/alertmanager/ and https://betterstack.com/community/guides/monitoring/prometheus-alertmanager/.
- **Correlation/routing layer (OSS):** Keep (MIT, ~12k★) ingests/ dedups/ correlates alerts and runs declarative YAML workflows; note it has **no native on-call scheduling** — https://github.com/keephq/keep and the maintainer discussion https://github.com/keephq/keep/discussions/4036.
- **On-call caveat:** **Grafana OnCall OSS is archived (2026-03-24)** — do not build on it — https://github.com/grafana-cold-storage/oncall.
- **Recovery notifications:** emit a distinct *resolved* event that references the original incident, and support flap suppression (e.g., Alertmanager `send_resolved`); group resolved with the alert's fingerprint so the recovery is never orphaned.
- **Escalation:** multi-tier policy (primary → secondary → manager) with acknowledge timeouts and repeat intervals; page only if unacknowledged within SLA.

**Concrete gap / upgrade for us**
1. Give every watchdog alert a **stable fingerprint** (e.g., `stage + component + error-class`) so repeated failures dedupe instead of spamming.
2. **Inhibit** downstream alerts when a root-cause alert fires (e.g., suppress "stage timeout" alerts while "GH_TOKEN missing" is active — exactly the failure mode seen in `standards/PIPELINE_VERIFICATION_REPORT.md`/SOP: 15/16 stages pass, 1 fails on a missing token).
3. **Implement resolved notifications** for our `heartbeat_stale`/stage-failure alerts; today the watchdog likely only fires on failure, not on recovery.
4. Adopt **Keep (MIT)** only if we need cross-source correlation; otherwise a lightweight dedupe-key + escalation table is enough.

---

### 2.4 Zero-trust CI/CD + secret handling for GitHub Actions cron pipelines

**Best practice**
- Follow GitHub's secure-use guide: least-privilege `permissions:`, avoid `pull_request_target` with untrusted code, mask secrets — https://docs.github.com/en/actions/reference/security/secure-use.
- **OIDC instead of long-lived cloud creds** — short-lived tokens, no stored credentials — https://blog.gitguardian.com/github-actions-security-cheat-sheet/ and GitHub's OIDC docs.
- **Pin every third-party action to a full commit SHA** (tags are movable); since Aug 2025 GitHub can *block/warn* on unpinned actions — https://github.blog/changelog/2025-08-15-github-actions-policy-now-supports-blocking-and-sha-pinning-actions/ and https://www.stepsecurity.io/blog/pinning-github-actions-for-enhanced-security-a-complete-guide.
- Tooling: **zizmor** (MIT, 6.7k★) static analyzer, **actionlint** (MIT, 4.3k★), **pinact** (MIT, 1.2k★) auto-pinning, **Harden-Runner** (Apache-2.0, 1.3k★) egress allowlisting. URLs: https://github.com/woodruffw/zizmor, https://github.com/rhysd/actionlint, https://github.com/suzuki-shunsuke/pinact, https://github.com/step-security/harden-runner.
- Use **GitHub Environments** with required reviewers for prod; store secrets in an external manager (Vault/AWS Secrets Manager/Key Vault) fetched at runtime via OIDC.

**Concrete gap / upgrade for us**
1. Our failure `heartbeat_stale` is caused by a **placeholder `GH_TOKEN`** (per SOP §"当前状态"). Move to a real, least-privilege token and, where cloud resources are touched, **OIDC** so no long-lived secrets sit in repo settings.
2. **Pin all Actions to SHAs** and add `zizmor` + `actionlint` as a PR check; run `pinact` to auto-fix.
3. Add **Harden-Runner** in audit mode, then egress-allowlist our cron's endpoints.
4. Separate prod secrets via **Environments + required reviewers**; never let a cron job on `main` use dev-scoped secrets and vice-versa.

---

### 2.5 Safe, rate-limited content distribution to social platforms

**Best practice**
- **Honor the platform's limit signal:** on HTTP 429 use the `Retry-After` / reset header, then exponential backoff **with full jitter**, with a hard attempt cap — never retry immediately (retry storms) — https://docs.x.com/x-api/fundamentals/rate-limits and https://social-api.ai/blog/social-api-rate-limits.
- **Queue writes below the ceiling** and process with a single policy layer; prefer webhooks over polling; cache slow-changing reads — same source, plus https://truto.one/blog/best-practices-for-handling-api-rate-limits-and-retries-across-multiple-third-party-apis/.
- **Per-account, per-platform token buckets** (sliding hourly/daily windows) to avoid one account exhausting the app quota.
- **Idempotency keys** per post so a retry never double-posts; draft→approval→publish workflow.
- **OSS distribution engines:** Postiz (AGPL-3.0, 37k★, uses Temporal) https://github.com/gitroomhq/postiz-app — note AGPL; Mixpost (self-host Lite free / Pro one-time license) https://mixpost.app/ — no copyleft.

**Concrete gap / upgrade for us**
1. Route all social output (from the content官/follow-up stages) through **one queue** with per-account token buckets + jittered backoff; today's pipeline likely posts synchronously inside a 30s stage, which is fragile under 429.
2. Add **idempotency keys** (content hash + account + date) and a **draft/approval** state so an LLM retry cannot double-post.
3. Surface platform 429s to the **watchdog** as deduped alerts with recovery notifications (see 2.3).
4. If self-hosting a scheduler, prefer **Mixpost** (avoids AGPL) or use Postiz only as an internal tool under its AGPL terms.

---

## Priority gaps (one-screen summary)

| # | Capability | Biggest gap today | Highest-value fix |
|---|---|---|---|
| 1 | Repo anti-hallucination | SOP checks existence/license/freshness but **not vulnerabilities or `archived`** | Add OSV.dev + `archived` + Scorecard gate; store provenance in `reuse_candidates.yml` |
| 2 | Payment webhooks | Unknown whether amount/order are cross-checked before crediting | Fail-closed amount+order+sign gate + `notify_id` idempotency + reconciliation job |
| 3 | Watchdog | Fires on failure, likely **no resolved/dedup/inhibit** | Stable fingerprints + inhibit rules + recovery notifications |
| 4 | CI/CD secrets | Real failure = placeholder `GH_TOKEN`; likely unpinned actions | OIDC + SHA-pinned actions + zizmor/actionlint + Harden-Runner |
| 5 | Content distribution | Synchronous posting, no queue/throttle/idempotency | Single queue + per-account token buckets + jittered backoff + idempotency keys |
| — | Product | Pay-per-play vs all-free rivals; no CN distribution rails | Add feed/remix + tournaments + rewarded ads; consider WeChat/Douyin mini-game channel (with 备案) |

---

## Verification & uncertainty log

- Star counts and release recency captured **2026-10-12** from `img.shields.io/github/{stars,v/release,release-date,license}/...`.
- **Licenses confirmed by source:** Apache-2.0 (Crawl4AI, Crawlee, Prefect, Airflow, Dagster, Hyperswitch, Kill Bill, OSV-Scanner, Scorecard, Harden-Runner); MIT (Temporal, zizmor, actionlint, pinact, OpenHands, SWE-agent, Keep, Medusa core); AGPL-3.0 (Firecrawl, Lago, Twenty, EspoCRM, Ever Gauzy, Postiz, Grafana OnCall, A1111); GPL-3.0 (ERPNext, ComfyUI); BSD-3-Clause (Saleor); n8n = **Sustainable Use License** (fair-code, non-OSI).
- **UNVERIFIED:** Vendure license (sources conflict MIT vs GPLv3); EvoAgentX license; Plutus/百度秒哒/App store pricing details; the "10M MAU" Astrocade figure; the reported Prefect→Dagster acquisition (statements exist from both companies but verify independently before relying on it).
