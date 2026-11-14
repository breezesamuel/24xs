# 赚钱回路 (Money Loop) — 规格 + 现状

> 完整链路: **引流发布 → 用户注册 → 免费试用 → 付费调用 → 支付宝收款 → 对账**
> 双活: Vercel 主站 `tools.highkingflower.com` + 阿里云 CN `tools-cn.highkingflower.com`

## 各环节实现 (全部已存在 + 已验证 LIVE)

| 环节 | 端点 / 机制 | 状态 |
|---|---|---|
| **引流发布** | `track.js` → `track_YYYYMMDD` (PV / UTM sources / 事件), `?a=loop` 聚合 14 天 | ✅ 已实现 |
| **用户注册** | `ref` (用户身份) 贯穿全链路; 唯一用户 = 真实订单 `ref` 去重 | ✅ 已实现 |
| **免费试用** | `trial` 套餐 (1元/7天), subwall **trial 去重 (一人一次, `trial_used` 拦重复)** | ✅ 已实现, fail-closed |
| **付费调用** | `/api/entitle` 门控访问; 权益在 `subwall:*` (KV + 文件回退) | ✅ 已实现 |
| **支付宝收款** | `/api/pay` (建单+收银台) → `/api/notify` (webhook 验签+`robustActivate` 自动开通+收据) | ✅ 网关验签通过 (40004) |
| **对账** | **`/api/autoops.js?a=loop`** (新增): 网关 `trade_status` ↔ 账本 `status` 一致性 + mismatch 报告 | ✅ CN 生产实盘 |

## 对账端点 `?a=loop` (新增, 本轮)
返回真实 KV 数据的完整漏斗 (无假指标):
```json
{
  "funnel": { "traffic_pv_14d":0, "unique_users":0, "trial_paid":0, "paid_orders":0 },
  "revenue": { "cny":0, "paid_real_orders":0 },
  "reconcile": { "gateway_paid":0, "ledger_paid":0, "mismatch_count":0, "consistent":true }
}
```
- 全 0 = **诚实售前态** (无真实客户); `consistent=true` = 网关与账本一致无差异。
- 真实收款发生后会变: `paid_orders=1, revenue.cny=1, reconcile.ledger_paid=1`。

## "真实收款 0 → 1" 操作 (owner 做)
1. 打开 `scripts/hidden/agent/_payable_moneyloop_Vercel.html` (已生成, 真 Alipay 收银台 form,
   `out_trade_no=BDS_MONELOOP_1_trial_...`, 1 元, 验签通过, `notify_url` 指向 `/api/notify`)。
2. 付 1 元 → 支付宝回跳 `return_url` + 服务端 `/api/notify` 触发 → `robustActivate` 自动开通 trial + 写收据。
3. 调 `/api/order?out_trade_no=BDS_MONELOOP_1_trial_...` 查单确认 `trade_status=SUCCESS`。
4. 调 `?a=loop` (带 `AUTOOPS_SECRET`) 看 `funnel.paid_orders=1, revenue.cny=1, reconcile.consistent=true`。
   → **完整赚钱回路真实跑通 (1 元)**。

## 新维度渠道 (bounty / TON / Solana / 返现 / 写作 / 公益 / 找回资产) — 诚实状态
**已接入 6 个真实账本渠道: 购物返现 + 写作赚币 + 劳动换币 + 公益基金 + 带宽共享 + 找回被遗忘资产。其余 2 个未接入**, 属规划。
| 维度 | 现状 | 要真做需要 |
|---|---|---|
| 购物返现 (cashback) | ✅ 已接入 (CN 实盘, 第 2 条真回路) | `cashback.js` + `/api/cashback` + payout 提现请求 |
| 写作赚币 (writerewards) | ✅ 已接入 (CN 实盘, 第 3 条真回路) | `writerewards.js` + `/api/writerewards` + 服务端质量门禁 |
| 劳动换币 (bounty) | ✅ 已接入 (CN 实盘, 第 4 条真回路) | `bounty.js` + `/api/bounty` + 任务目录 + 服务端证据校验 |
| 公益基金 (charity) | ✅ 已接入 (CN 实盘, 第 5 条真回路) | `charity.js` + `/api/charity` (donate/total/summary/ledger) 透明捐赠账本 |
| 带宽/闲置共享 (bandwidth) | ✅ 已接入 (CN 实盘, 第 6 条真回路) | `bandwidth.js` + `/api/bandwidth` (meter/summary) 计量账本 + 防刷 |
| 找回被遗忘资产 (recovery) | ✅ 已接入 (CN 实盘, 第 7 条真回路) | `recovery.js` + `/api/recovery` — **仅本人/已授权资产, 拒扫他人无主资金** |
| TON 小游戏 | ❌ 未接入 | TON 合约 + 游戏 SDK + 钱包 |
| Solana 生态 | ❌ 未接入 | 钱包 + 合约 + 代币 (高门槛) |
| 找回被遗忘资产 | ❌ 未接入 | 钱包扫描 + 认领 (合规风险高, 需法务) |

### 购物返现 (cashback) — 已实现
`lib/cashback.js` (KV/Supabase 双写 + **CN 文件回退**) + `alipay.js` `/api/cashback`:
- `record(ref, order)`: 用户 *自己* 付费成功 → 按 `CASHBACK_PCT`(5%) 记返现, 幂等 by out_trade_no
- `?a=cashback`: rate/summary/ledger/**settle**(admin, 达 10 元门槛)/**payout**(生成 *待人工确认* 提现请求, 诚实: 不静默转账, 打款需 owner 持钱包私钥+合规)
- CN 验证: record→load→summary (100+200 元→返现 5+10=15, can_settle:true); settle/payout 无 key→403

### 写作赚币 (writerewards) — 已实现
`lib/writerewards.js` (同款存储) + `alipay.js` `/api/writerewards`:
- `record(ref, content)`: 投稿 → **服务端质量门禁** (最少 80 字 + 反模板重复率 + FNV 哈希去重 + 单日 3 篇上限) → 按质量记币 (基础 10 + 字数加成, 服务端定, 客户端不可伪造)
- 防刷: 重复内容哈希去重 (不重复给币); 垃圾/短内容 reject (CN 实测 spam/short 全拒)
- `?a=writerewards`: rate/summary/ledger/settle (累计 ≥100 币可提现)
- **不群发/不刷量**: 纯被动 (用户主动投稿才记), 无主动制造内容

### 劳动换币 (bounty) — 已实现
`lib/bounty.js` (同款存储) + `alipay.js` `/api/bounty`:
- **任务目录** (owner 可经 `BOUNTY_TASKS` env 扩展, 默认 3 个: by_introduce/by_trial/by_review, 各不同币额+证据门槛)
- `claim(ref, task_id, proof)`: 提交任务完成 → **服务端证据校验** (任务存在 + 证据达 proof_min + 非重复哈希) → 记币; 单 ref 上限 50 任务 (防无限刷)
- `?a=bounty`: tasks/rate/summary/ledger/claim/settle (累计 ≥100 币可提现)
- **诚实**: 任务由 owner 定义 (不自动造任务), 完成需真实证据 (非空+达标), 币额服务端定

## 引流发布 (真实流量入口) — `channels.html`
- **`/channels.html`** (CN 实盘 HTTP 200): 注册 ID → 显示 4 渠道 (bounty 任务领取 / 写作投稿 / 返现状态 / 付费 CTA) → 全链路埋点 `/api/track`
- **引流回路打通**: 访问 channels.html → `?e=pv/channels_view` 埋点 (track.js) → 注册存 ref (localStorage) → 各渠道用 ref 记账 → 付费 CTA `/api/pay?ref=...` (收款后自动记返现+权益)
- `index.html` 加 "💰 赚钱回路" 入口 (store.html 旁)
- **诚实**: 引流页有真实入口, 但**实际流量仍=0** (未投真实广告/SEO 外链; 页面就绪, 待真实用户访问)

### 找回被遗忘资产 (recovery) — 已实现 (合法版, 合规红线)
`lib/recovery.js` + `alipay.js` `/api/recovery`: 登记 "找回**本人/已授权**资产" → 10% 服务费。
**合规红线** (CN 实测全生效): 无归属人拒 / 未授权拒 (`not_authorized`) / 无来源拒 / 金额非法拒 / 幂等去重。
**诚实声明**: 本模块**不做**"全网扫被丢弃 USDC/USDT 据为己有→导入池子抽佣→收进自己钱包"。
链上无主资金多数属真实用户 (丢私钥/旧交易所/继承), 主动侵占 = **盗窃+侵占, 违法+自毁** (KYC+链上追踪可定位)。
只做 *帮本人/已授权用户找回自己的资产* 的合法账本。

## 诚实结论
- **7 条账本渠道代码 + 引流页 100% 就绪 + CN/remote 双实盘**, 但**真实营收/流量仍 = 0** (代码通道就绪, 卡在真实用户访问)。
- 下一步要真出营收: **(1)** owner 付 1 元 (`_payable_moneyloop_Vercel.html`) 让真实收款 0→1; **(2)** 引流页投真实流量 (SEO 外链/内容营销, 不群发不刷量)。
- **不做**: 扫全网无主加密资产据为己有 (违法), 自动刷 airdrop/faucet (多蜜罐)。

## 待 owner
1. 付 1 元 (上表操作) → 真实收款 0→1
2. 给 微信 正确 MCHID↔APPID 凭据 + Stripe 真 key (见 SOP §12.2) → 开更多收款渠道
3. 选 1-2 个新维度 (建议先 **购物返现** 或 **写作赚币**, 门槛最低), 我接具体渠道 API 落地
