# 全网赏金扫描流程（可重复执行 · 2026-10-31 首轮结论）

## 首轮结论（诚实）
- **本轮无可认领的真实赏金**。GitHub 公开空间搜遍（commenter:algora-pbc[bot] 过滤）仅 16 条，其中：
  - `SecureBananaLabs/bug-bounty`（$430-$780，"AI agent friendly" 标签）= **星标农场实锤**：10,368 open issues、975 forks、5 个月 **0 个 merged PR**，487 条评论全是排队送工的 AI。永不投工。
  - `rohitdash08/FinMind`（4 个 fintech 功能赏金）= 仓库 2 月 21 日后无维护，18 个 merged PR 全在死前。没人合并=没人付款。弃。
  - `microg/GmsCore` $2,340 WearOS = 数周级巨型任务，单人风险不成比例。
- **真实付款证据的平台**：Algora（Qdrant 已付列表 $150-$360 可见）。开放赏金在其 SPA 面板内，API 搜索不可见——需浏览器/控制台访问。

## 可重复扫描流程（每轮 ~5 分钟）
1. `gh auth token` → GET /search/issues `q=label:bounty state:open no:assignee commenter:algora-pbc[bot]` sort=created desc（注意搜索次级限流：两次搜索间 sleep 30+）
2. 跳过 org:SecureBananaLabs 与 created < 近 60 天的
3. 对候选：GET repo 详情验证 **merged PR 存在** + repo `pushed_at` 距今 < 30 天（活人才会合并付款）
4. 通过验证 → 在 issue 评论 `/attempt`（breezesamuel 身份）→ 实现 → PR 带 `closes #N`
5. 补充面板探测：WebFetch `https://algora.io/<org>/bounties?status=open`（Qdrant 已验证该 URL 模式有效）
6. 打款环节：Stripe KYC（需要用户身份一次性完成）；加密赏金（Superteam Earn，Solana USDC 直付钱包 `4moYJshT...`，无 KYC）登录走 Google OAuth（用户浏览器）

## 已验证的付款方名单（可投工）
- Qdrant（向量数据库，$150-$360/单，C++/Rust 为主——需评估栈匹配）
- 待增补：每日扫描中遇 merged 付款实绩的新 org
