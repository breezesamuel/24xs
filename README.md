# 24xs · AI 交付工厂

> 目标：24 小时内把这一个空文件夹，变成**能在半年内支撑 1000 万进账的机器**。
> 状态：**基础引擎 7-7 通过；资金栈 20 项安全测试通过；情报 MCP 已接真实数据。118 个文件 / 2.38 MB。**
> 每日自动任务 `AI_Engine_Daily`（每天 08:50）已含三段：引擎全流程 + 资金安全回归 + 情报刷新。
>
> ⚠️ **资金边界（不可绕过）**
> 报税申报、分红付款、开票属于法定行为。本仓库在未接入官方接口并完成核验前**一律拒绝执行**（fail-closed），
> 必须由持证会计或两名不同自然人人工完成。**不存在"全托管自动付款"**，这是设计而非缺陷。
> 详见 `08_军团/capital/SECURITY.md`。

---

## 三十秒看完

**你在卖什么**

GEO（Generative Engine Optimization）服务：让品牌在 AI 搜索/回答里被引用，而不是只出现在传统搜索排名里。
交付物是"可复现的诊断 + 可执行的改造清单"，不是 PPT。

**每天自动产出什么**

| 产出 | 位置 | 能不能直接用 |
|---|---|---|
| 探测快照（多引擎问答实测） | `99_产出/报告/` | 是真实读库数据，非模拟 |
| A 档触达队列 CSV | `99_产出/获客名单/` | 文案已去重，**联系人需自行核验** |
| 内容资产（35 篇） | `99_产出/内容/` | 可直接发 |
| 报价与底线 | `99_产出/报告/` | 成本 `99,357`，报价下限 `221,000` |
| 每日看板 | `99_产出/报告/最新看板.md` | 每天一个，只问一件事 |
| 失败项目情报 | `08_军团/intel/` | 已接真实 MCP（1749 条记录） |

**四个目录一句话**

```
00_战略/     为什么做、怎么算账、什么时候停
01_引擎/     零依赖 Python 工厂（内容→探测→潜客→触达→测算→看板）
05_财务/     现金流、成本、收款（人工）
07_运维/     每日自动任务、日志、备份
08_军团/     AI Worker Swarm：情报→线索→实验→账本→资金（默认全关）
```

---

## 一、这套系统现在能做什么

### 1. 基础引擎（零外部依赖，`python cli.py all`）

```
内容资产/  corpus_gen.py          内容生成  └ 每日 7 篇可直接发
内容资产/  geo_audit.py           GEO 审计  └ 读库产出真实探测快照
获客/      lead_gen.py            潜客评分  └ 按可购买性排序
获客/      outreach.py            触达文案  └ 开场/桥接/价值点/CTA 四层轮换
财务/      finance.py             成本与报价 └ 硬底线，不让亏本接单
测试/      verify.py              十三项自测  └ GM 视角：能不能留下并自己跑
```

**验收（`python -X utf8 verify.py` → 17/17）**

```
[PASS] 1  看板有真实数字          [PASS] 10 资金安全门禁有效 (20 tests)
[PASS] 2  真实名单质量            [PASS] 11 Node 工具链可用
[PASS] 3  内容可直接发布          [PASS] 12 情报来自真实 MCP
[PASS] 4  数据库有真实读库数据    [PASS] 13 重跑不累积数据
[PASS] 5  报价有硬底线            [PASS] 14 生产域名在线（关机可用）
[PASS] 6  测算是诚实的            [PASS] 15 官网有可用转化入口
[PASS] 7  明天知道怎么自动跑      [PASS] 16 已核验名单未自动外发
[PASS] 8  官网文案不虚假承诺      [PASS] 17 联系方式格式卫生
[PASS] 9  7x24 看护已就位
```

> 当前 **17/17**。第 15 项只要有**真实可用的邮箱或微信号**即转绿（当前走邮箱 `460123249@qq.com`）。
>
> 第 2 项校验的是**真实核验名单**（条数 / 报告配套 / 占位符清零 / 隔离状态），
> 不是旧的合成触达队列——那份队列按设计绝不外发，拿它当验收标准等于奖励造假。
>
> 第 17 项用 `01_引擎/phoneutil.py` 复核库里每个号码：真实区号白名单 +
> 座机必须带分隔符 + 400 按位数判定，防止网页 `<script>` 里的数字串被当成联系方式。

> ✅ `cli.py all` **已幂等**：`leads.company`、`outreach(lead_id,channel,template)`、
> `geo_probes(client,platform,question)`、`corpus(industry,kind,title)` 均加唯一索引，
> 写入改用 `INSERT OR IGNORE` / `ON CONFLICT DO UPDATE`。
> 迁移顺带清掉了历史重复：触达 937→172、探测 5280→1344、语料 315→35。
> 验收见 `python -X utf8 test_idempotency.py`（连跑 3 次计数必须不变）。

### 7x24 常驻与公网访问

**生产地址：<https://geo-audit-24xs.vercel.app>**
托管在 Vercel CDN，**电脑关机/断电后依然可访问**。Quick Tunnel 只用于本机调试。

| 组件 | 说明 |
|---|---|
| `07_运维/deploy_site.py` | 同步官网到生产域名。按 `index.html` 内容哈希判断，未变化则跳过；`--force` 强制重部 |
| `07_运维/watchdog.py` | 本机静态服务 + 隧道 + 子进程自动重启 + 每 6h 流水线 |
| 计划任务 `24xs_Watchdog` | 登录即启、崩溃 1 分钟重启、**运行时长无上限**（默认 72h 会截断） |
| `07_运维/install_watchdog_task.py` | 注册/查询该任务（`schtasks` 需管理员，改走 PowerShell 计划任务 API） |
| `07_运维/watchdog/state.json` | `public_url`、`public_http`、心跳时间、子进程存活与重启次数 |

> 注意：本机开了代理 `127.0.0.1:7897`，`curl` 和 Python `urllib` **不读** WinINET 设置，
> 直连会 timeout。`deploy_site.py` 已内置代理探测，只有站点真挂了才算失败。

### 官网转化入口

`10_官网/index.html` 里改一处即可上线：

```js
var CONTACT_EMAIL  = "460123249@qq.com";  // 已有，mailto 按钮直接可用
var CONTACT_WECHAT = "";                   // 留空 = 不显示微信区
```

- 把微信二维码图片命名为 `wechat-qr.png` 放进 `10_官网/`，页面自动显示（没有就只显示邮箱入口）
- 表单只在浏览器里把填写内容拼成一段文字，**不上传任何服务器**，用户复制后发给你
- `verify.py` 第 15 项只要有**真实可用的邮箱或微信号**就转绿（已按此判定，不看源码里有没有 `REPLACE_ME`）

### 收款：MoltsPay（USDC，走 x402 协议）

生产 webhook 已上线并通过安全测试：

```
POST https://geo-audit-24xs.vercel.app/api/webhook/moltspay
```

- 代码在 `10_官网/api/webhook/moltspay.py`。**必须放在 `10_官网/` 里**——
  `deploy_site.py` 的 `SITE_DIR` 指向该目录，写在仓库根目录的 `api/` 永远不会被上传
- 验签按官方规范：`X-X402-Signature` + `X-X402-Timestamp`，对 `{timestamp}.{raw_body}` 做 HMAC-SHA256
- 未配置 `MOLTSPAY_WEBHOOK_SECRET` 时返回 **503 且不处理任何事件**（fail-closed）
- 时间戳容差 300 秒防重放；按事件 `id` 幂等去重
- 安全用例见 `python -X utf8 08_军团/experiments/test_webhook_local.py`（9/9）

⚠️ 两个必须知道的外部约束：
- **Webhook 是 Pro / Business 套餐功能**，免费账号注册会返回 `403`
- 产品付款链接形如 `/p/<slug>`；需在 Dashboard → Webhooks 创建并复制签名密钥，
  再设为 Vercel 环境变量 `MOLTSPAY_WEBHOOK_SECRET`

**目前仍未完成**：产品未创建、无签名密钥、无收款账户、无 KYC。收款闭环尚未跑通。

### 导入真实名单（当前唯一的一万块卡点）

`offline_lead_gen.py` 产出的是 `random` 生成的假公司、假联系人，
证据链接是 `f"#result_{random.randint(1,50)}"`，CSV 里连电话邮箱字段都没有——**那份不能发**。

```powershell
# 1. 生成标准模板
python -X utf8 08_军团\experiments\import_verified_leads.py --template 99_产出\获客名单\真实名单模板.csv

# 2. 你手工填真实公司（公司/官网/联系人/电话或邮箱或微信 必填），删掉示例行
# 3. 先 dry-run 看校验结果
python -X utf8 08_军团\experiments\import_verified_leads.py --csv 你的名单.csv --dry-run

# 4. 校验全过才入库
python -X utf8 08_军团\experiments\import_verified_leads.py --csv 你的名单.csv
```

约束：**任何一行不合格就整批拒绝**，不做部分导入。入库后状态是 `new_verified`，
不进入任何自动发送队列（`verify.py` 第 16 项守住这条）。

### 2. 资金栈（`08_军团/capital/`）

| 能力 | 状态 |
|---|---|
| 支付宝 RSA2 验签 + form 解码 | 已实现，验签失败一律拒绝 |
| 微信 APIv3 验签 + `AEAD_AES_256_GCM` 解密 | 已实现，未配置平台公钥则拒绝**所有**回调 |
| 报税申报提交 | **永远返回 `False`**，须人工在电子税务局申报 |
| 分红计算 | 产出待审草稿，不自动批准、不自动付款 |
| 分红付款 | 默认拒绝；需双人审批 + `approval_evidence` + 两人互不相同 |
| 银企直连 EBICS | 未实现，明确失败，不静默降级 |

```powershell
python -X utf8 08_军团\capital\tests\test_security.py   # 20 项安全回归
```

**账本口径**（回归重点）

```
可用余额 = 桶分配额 - Σ max(allocated_cny, spent_cny)   # status ∉ {cancelled, reinvested}
```

旧实现只统计 `active` 且只看 `spent_cny`，导致实验关闭后预算被"退还"，
First Money 因此被误跑两次（净亏 2000 元却显示实验桶仍有 4000 可用）。现已修正。

### 3. 情报（`08_军团/intel/`）— 已接真实数据

`lootdrop_intel.py` 通过 **stdio MCP（JSON-RPC）** 调用 `mcp-lootdrop`，已验证可用：

```
tools: lootdrop_diagnose, search_startups, get_startup, list_rebuild_ideas,
       failure_landscape, graveyard_stats, random_loot, top_startups, list_facets
数据量: startups 1749 行 / dashboard_analytics 596 行
```

Windows 上有三个必须处理的坑（均已修复）：

1. `npm/npx` 只有 `.cmd`/`.ps1` 变体，`subprocess` 直呼裸名报 `[WinError 2]` → `workers/node_bridge.py`
2. `mcp-lootdrop` 是 **stdio 服务器**（打印 `ready (stdio)`），把参数当命令行传永远拿不到数据 → `intel/mcp_client.py`
3. MCP 返回 **markdown 而非 JSON**，`raw.get("data")` 恒为空 → `_parse_markdown_listings()`

真实数据的筛选结果比离线兜底严格得多（市场潜力 ≥ 70、非 hard、可扩展性非 low、本金 ≤ $15k）：
当前实际命中 **1 个**（Pluralsight，市场潜力 80，本金 $10k，MVP 4 周）。
离线兜底的 4 条是人工挑选的样本，**不可与真实结果混为一谈**。

---

## 二、需要你动手的（自动化不会替你做）

| 事项 | 为什么必须人工 |
|---|---|
| 税务申报 | 法定申报行为，需持证会计与实名账号 |
| 分红付款 | 资金流出，需两名不同自然人审批 |
| 开票 | 增值税行为，需真实开票资质 |
| 登录/验证码/2FA | 我不会绕过平台风控 |
| 批量对外发送 | 受《个人信息保护法》《广告法》约束，需合法依据 |

技术性、本地可逆、无资金影响的动作（跑流水线、生成报告、跑测试、情报抓取）**可以无人值守**，每日任务已覆盖。

---

## 三、当前真实状态（不粉饰）

- **收入 `0 元`。** 没有任何客户回复、签约或回款。
- **名单未核验。** `offline_lead_gen.py` 产出的是高仿真公司池，联系人/邮箱/电话/证据链接**均未核实**，不能称为真实线索。
- **GEO 报告含 `baseline-sim` 基线**，不能作为付费诊断结果出售。正式销售前需真实探测数据与可回溯证据。
- **报税税额算法是简化的**（收入×6%、支出×6% 一刀切），**不是申报依据**。
- **支付/开票服务商 API 尚未核验**，示例 URL 与字段为占位实现。

要拿到第一个 1 万，下一步不是加功能，是：
定义一个**独立付费 SKU**（如真实 GEO 诊断快检）→ 取得真实探测数据 → 建立 50 家已核验 ICP → 合法触达 → 跟踪到回款。

---

## 四、每天怎么跑

```powershell
# 全流程
cd 01_引擎; python -X utf8 cli.py all

# 自测
python -X utf8 verify.py

# 资金安全回归
python -X utf8 08_军团\capital\tests\test_security.py

# 情报刷新（真实 MCP，失败自动退回离线兜底）
cd 08_军团; python -X utf8 intel\lootdrop_intel.py

# Node 环境自检
python -X utf8 08_军团\workers\node_bridge.py
```

每日自动任务：`AI_Engine_Daily`（每天 08:50）
手动触发：`Start-ScheduledTask -TaskName "AI_Engine_Daily"`
日志：`07_运维\daily.log`（含三段结果；安全测试失败会打 `[ALERT]`）

---

## 五、文件地图

```
00_战略/                  战略、现金流模型、决策规则
01_引擎/                  零依赖 Python 工厂 + verify.py
  00_配置/                行业、成本、Token 单价
  01_内容/                corpus_gen.py
  02_GEO审计/             geo_audit.py
  03_获客/                lead_gen.py, outreach.py
  04_财务/                finance.py
  05_测试/                verify.py
  README.md               引擎内部说明
02_交付物/                交付模板
03_获客/                  获客 SOP、话术
04_内容/                  内容 SOP
05_财务/                  01_现金流与收款策略.md（+ 待补 02/03）
06_情报/                  情报来源清单
07_运维/                  run_daily.ps1, install_daily_task.ps1, daily.log, backup/
08_军团/                  AI Worker Swarm
  SECURITY→ capital/      资金栈 + SECURITY.md + .gitignore + 模板
  intel/                  lootdrop_intel.py, mcp_client.py
  workers/                page_agent_worker.py, node_bridge.py, lead_gen
  experiments/            first_money_exp.py, RUN_FIRST_MONEY.bat, send_*.bat
99_产出/                  报告 / 获客名单 / 内容 / _data(factory.sqlite3)
```

---

## 六、变更记录

第 53 轮：资金栈安全收口（清除硬编码 PII、报税/分红 fail-closed、账本口径修正）+ 20 项安全测试
+ 真实 Loot Drop MCP 接入（stdio JSON-RPC 客户端、markdown 解析、枚举修正、Node 跨平台定位）
+ 每日任务扩展为三段。
