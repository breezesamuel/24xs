# RapidAPI Listing Kit — AI Automation Platform (5 Deterministic Agents)

> 目标：把 https://bingdashanai.highkingflower.com/agents/ 的 5 个确定性 agent 上架 RapidAPI 市场。
> 你需要做的：注册 rapidapi.com 账号 → Provider Dashboard → Add New API → 粘贴本包内容。
> 预计耗时 20-30 分钟。本包由自动化于 2026-10-25 生成。

---

## 1. Listing 文案（直接粘贴）

**API Name**: `Deterministic AI Agents — Code · Data · Finance · Process · Sales`

**Tagline**: No-hallucination task agents with identical outputs for identical inputs. JSON in/out.

**Category**: Tools → Productivity  (备选: AI/ML → Machine Learning)

**Description**:
```
Five deterministic agents for everyday business work — built for embedding:

• code    — generate & validate small utility functions with test-first templates
• data    — clean, normalize and cross-check tabular records (CSV/JSON)
• finance — compound interest, amortization schedules, margin/markup math, dunning scenarios
• process — approval chains, SOP checklists, onboarding plans
• sales   — quotation sheets, follow-up scripts, objection handling playbooks

Why deterministic? Same input always produces the same output. Every agent is
covered by automated tests (537 and counting), so you can put them inside
invoicing, CRM and compliance flows without babysitting a probabilistic LLM.

JSON in, JSON out. Synchronous /run and asynchronous /tasks + /queue/drain.
Per-user monthly quotas with /usage metering.

Base URL: https://bingdashanai.highkingflower.com/agents
Full OpenAPI 3.0 spec: /agents/openapi.json (70 paths)
Health check (free): GET /agents/health
```

**Logo**: 复用 https://tools.highkingflower.com/icons/favicon-192.png

## 2. Pricing Tiers（RapidAPI 计费，平台用 PayPal 给你分成）

| Tier | 月费 | 配额 | 超量单价 |
|---|---|---|---|
| Free | $0 | 25 calls/mo | — |
| Basic | $5 | 300 calls/mo | $0.02/call |
| Pro | $15 | 1,500 calls/mo | $0.015/call |
| Ultra | $49 | 6,000 calls/mo | $0.012/call |

（对齐主站订阅：¥60/月≈Basic、¥150/季≈Pro、¥500/年≈Ultra 的折算逻辑，别在同一市场里卖两套矛盾价。）

## 3. 端点与鉴权

RapidAPI 会用 `X-RapidAPI-Key` 代理调用；本平台自身鉴权是 Bearer Token（注册获得）。
**上架前唯一需要做的集成**（选一个）：
- A（推荐起步）: 手动模式——买家下单后你把 RapidAPI 用户映射到平台账号（发邮件给他们 token），文档里写清楚。
- B（自动化，我可代建）: 平台加一个 `/rapidapi/provision` 端点，凭 RapidAPI 转发的用户 key 自动注册并返回 token（需要你在 RapidAPI 侧开启自定义头转发）。

## 4. 代码样例（放进 Listing 的 Code Examples）

### cURL
```bash
# 1) register once → get token
curl -X POST https://bingdashanai.highkingflower.com/agents/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@corp.com","name":"You","company":"Corp","plan":"starter"}'

# 2) run the finance agent synchronously
curl -X POST https://bingdashanai.highkingflower.com/agents/run \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"agent":"finance","payload":{"task":"compound","principal":10000,"rate":0.05,"years":3}}'
```

### Node.js
```js
const base = "https://bingdashanai.highkingflower.com/agents";
const reg = await fetch(base + "/auth/register", {method:"POST", headers:{"content-type":"application/json"},
  body: JSON.stringify({email:"you@corp.com", name:"You", company:"Corp", plan:"starter"})}).then(r=>r.json());
const run = await fetch(base + "/run", {method:"POST",
  headers:{authorization:"Bearer "+reg.token, "content-type":"application/json"},
  body: JSON.stringify({agent:"data", payload:{task:"normalize", rows:[{a:" 1,000 "},{a:"2,500"}]}})}).then(r=>r.json());
console.log(run);
```

### Python
```python
import requests
base = "https://bingdashanai.highkingflower.com/agents"
tok = requests.post(f"{base}/auth/register", json={
    "email":"you@corp.com","name":"You","company":"Corp","plan":"starter"}).json()["token"]
out = requests.post(f"{base}/run", headers={"Authorization":f"Bearer {tok}"},
    json={"agent":"process","payload":{"task":"approval_chain","steps":["draft","review","approve"]}}).json()
print(out)
```

## 5. 上架检查单
- [ ] openapi.json 已快照在本目录（可直接上传 RapidAPI）
- [ ] Health 端点免费且 200（已完成，多次实测）
- [ ] 定价表与主站不冲突（§2）
- [ ] 鉴权集成模式选定（§3 A 或 B）
- [ ] Logo URL 可访问（§1）

## 6. 诚实备注
- 上架后收入走 RapidAPI 的分成体系（PayPal 月结），不经过我们的支付宝。
- 免费档每天配额可以随时调；先低后高，避免被刷。
- 平台 /agents/health 是唯一公开免鉴权端点，其余全部要 token——上架不会暴露任何管理面。
