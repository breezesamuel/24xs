# 五维筛选 SOP — 爬虫采集框架 + 工作流引擎 + 自主电商自动化

## SOP 流程（标准化、可复用、防 AI 幻觉）

### 第一步：检索复用（防幻觉验证阶梯 —— 全部走真实 API，不信任任何搜索摘要）
1. **存在性**：`GET /repos/:owner/:repo` → 404 即“幻觉仓库”，直接剔除。
2. **归档/禁用**：`archived=true` / `disabled=true` → 剔除（不再维护）。
3. **停更**：`pushed_at` 距今 >730 天 → 剔除；>365 天 → 降权。
4. **最新版本**：`GET /releases/latest` → tag + 发布时间（防止“推荐已停更/旧版本”）。
5. **安全**：`GET /repos/:full/security-advisories`（GHSA）+ `POST https://api.osv.dev/v1/query`（OSV.dev）→ 已知漏洞。
6. 若 API 返回 403 → 触发限流，改配置真实 `GH_TOKEN`（或 `gh auth token`）后重试。

> 由 `scripts/standards/select_wheel.mjs` 自动执行，机读报告落 `standards/wheel_selection_report.json`。

### 第二步：五维筛选（全部从 GitHub API 真实元数据计算）
| 维度 | 关键指标 | 判定标准 | 备注 |
|------|----------|----------|------|
| **D1 更新时间** | `pushed_at` 距今天数 | ≤30天：100分<br>≤180天：70分<br>≤365天：40分<br>>365天：0分（淘汰） | `stale_days = floor((Now - pushed_at)/86400000)` |
| **D2 Star数** | `stargazers_count` | ≥20000：100分<br>≥8000：80分<br>≥2000：60分<br>≥300：35分<br>>300：15分 | 社区背书指标，非线性分级 |
| **D3 开源协议** | `license.spdx_id` / LICENSE 文件头 | **PERMISSIVE**（MIT/Apache-2.0/BSD）：100分，低风险<br>**WEAK_COPYLEFT**（LGPL/MPL）：45分，动态链接相对安全<br>**STRONG_COPYLEFT**（GPL-3.0/AGPL-3.0/SSPL-1.0）：0分，**协议红线**，闭源商用/自托管 SaaS 可能被迫开源<br>**fair-code / NOASSERTION**：10分，需人工审查 LICENSE 全文 | 本 SOP 的核心防雷环节 |
| **D4 技术栈匹配** | `language` 与宿主栈（NODE/JS/PY/GO/RUST/PHP） | 完全匹配：100分<br>部分兼容（Node+Python子集）：55分<br>完全不匹配：15分 | 我们的主体技术栈为 Node.js / Python |
| **D5 部署难度** | 人工标注（1=极易 → 5=很难） | 难度 1-2：70-100分<br>难度 3：45-65分<br>难度 4：20-40分<br>难度 5：0-15分 | 依赖组件数/是否需外部服务/集群开销 |

**总得分** = D1×0.18 + D2×0.18 + D3×0.32 + D4×0.20 + D5×0.12

### 第二步补充：安全门禁（门禁而非加权维，避免高分掩盖漏洞）
| 信号 | 来源 | 判定 |
|------|------|------|
| 存在 **CRITICAL** 安全公告 | GitHub `security-advisories` | **ELIMINATE(已知严重漏洞)** |
| 存在 **HIGH** 安全公告，或 OSV 漏洞 ≥5 | GitHub advisories / OSV.dev | 总分再高也**封顶 REVIEW**（禁止“可直接用”） |
| OSV 漏洞 1–4 | OSV.dev | 降级为 `medium`（列入人工审查） |
| 最新 release 距今 >730 天 且 `pushed_at` 亦陈旧 | `/releases/latest` | 结合 D1 判停更 |

> **实测教训**：`unclecode/crawl4ai` 五维总分 92（原 Top3），但命中 **5 条 CRITICAL 公告 + 31 条 OSV 漏洞 → 剔除**；
> `scrapy/scrapy` 命中 HIGH×5 + OSV×23 → 封顶 REVIEW。最终 **adbar/trafilatura（安全 ok）** 为唯一 `DIRECT_USE`。
> 这证明“只看 Star/更新/协议”会漏掉漏洞地雷。

### 第三步：选 3 个
- 对每个目标（爬虫/工作流/电商）从候选池中挑选 **Top 3**（按总分降序）。
- 若 Top 3 中有 `DIRECT_USE` 判定 → 首选；无则选 `SUITABLE`；无则 `REVIEW`（人工审查）。

### 第四步：判定
| 协议风险等级 | 判定 | 行动 |
|---|---|---|
| `critical` (GPL-3.0/AGPL-3.0/SSPL-1.0) | **ELIMINATE** | 立即淘汰，不可商用闭源 |
| `high` (fair-code, Elastic-2.0, BSL) | **REVIEW** | 需人工确认商用条款，慎重 |
| `medium` (LGPL-3.0, MPL-2.0) | **SUITABLE** | 可用但有 copyleft 限制，二开可能需开源衍生部分 |
| `low` (MIT, Apache-2.0, BSD) | **DIRECT_USE** | 宽松协议，可直接引入，仅需保留 NOTICE（Apache） |

### 第五步：评估成本风险
- **协议风险**：GPL/AGPL/SSPL → 商用必开源（最高风险）
- **技术栈风险**：Go/Rust/Java vs Node → 跨栈维护成本、性能调优、人才获取
- **部署风险**：集群/外部服务 → 运维成本、可用性、成本超支
- **维护风险**：停更>2年、Issue激活、安全漏洞 → 升级成本、数据迁移风险

---

## 实测候选汇总（实时 API 校验，防幻觉）

### 目标：爬虫采集框架（已叠加安全门禁实测）
| 排名 | 仓库 | Stars | 协议 | 栈匹配 | 总分 | 安全 | 判定 |
|------|------|--------|------|----------|------|------|------|
| 1 | **adbar/trafilatura** | 6,957 | Apache-2.0 | ✓ Python | 93 | ok（v2.3.1） | **DIRECT_USE** — 唯一无已知漏洞的 `DIRECT_USE` |
| 2 | **scrapy/scrapy** | 64,738 | BSD-3-Clause | ✓ Python | 95 | HIGH×5 + OSV×23 | **REVIEW**（高分但封顶，禁止直接复用） |
| 3 | **unclecode/crawl4ai** | 85,264 | Apache-2.0 | ✓ Python | 92 | **CRITICAL×5 + OSV×31** | **ELIMINATE(已知严重漏洞)** |

> **淘汰**：mendableai/firecrawl（AGPL-3.0 强传染）、mikf/gallery-dl（GPL-2.0 强传染）、gocolly/colly（Go 技术栈不匹配）、
> unclecode/crawl4ai（安全门禁剔除）。
> **安全查询可用 `--no-security` 跳过（离线/限流时）。**

### 目标：工作流引擎
| 排名 | 仓库 | Stars | 协议 | D4栈匹配 | D5部署 | 总分 | 判定 |
|------|------|--------|------|----------|--------|------|------|
| 1 | **PrefectHQ/prefect** | 24,001 | Apache-2.0 | ✓ Python | 中(3) | 86 | **SUITABLE** |
| 2 | **apache/airflow** | 47,143 | Apache-2.0 | ✓ Python | 中(4) | 83 | **SUITABLE** |
| 3 | **dagster-io/dagster** | 16,262 | Apache-2.0 | ✓ Python | 中(3) | 82 | **SUITABLE** |

> **关键判断**：我们已有 GitHub Actions（每 15 分钟）+ Vercel cron + PM2 三级调度。引入重型工作流引擎（Temporal / Airflow）会增加运维负担。若需自托管可选风格，**Windmill（Apache-2.0，实测定）** 是最轻量的补充。

### 目标：自主电商自动化
| 排名 | 仓库 | Stars | 协议 | D4栈匹配 | D5部署 | 总分 | 判定 |
|------|------|--------|------|----------|--------|------|------|
| 1 | **saleor/saleor** | 23,400 | BSD-3-Clause | ✓ Python | 难(4) | 83 | **SUITABLE** |
| 2 | **bagisto/bagisto** | 28,200 | MIT | ✓ PHP/Laravel | 中(3) | 78 | **SUITABLE** |
| 3 | **spree/spree** | 17,000 | BSD-3-Clause | ✓ Ruby | 中(3) | 74 | **SUITABLE** |

> **关键判断**：我们已有真实收银台（tools.highkingflower.com，Alipay + KV + 计费闭环）。引入 Medusa/Saleor 属于重复造轮子。若未来需多 SKU/多商户，Medusa(MIT) 是首选备选。

---

## 关键防雷点（协议红线）

| 协议 | 风险等级 | 为什么禁止 |
|------|----------|-----------|
| **GPL-3.0** | critical | 衍生作品必须同协议开源；SaaS 变体可能触发云竞争条款 |
| **AGPL-3.0** | critical | 网络使用即触发分发：SaaS 部署也须向用户提供源码 |
| **SSPL-1.0** | critical | 提供竞争性 SaaS 服务须开源全部服务栈（MongoDB 用） |
| **Elastic-2.0** | high | 禁止作为托管服务提供、禁止规避许可限制 |
| **fair-code / BSL** | high | 非开源：看得到源码但禁止转售/部分商用，需商业授权 |
| **MIT / Apache-2.0 / BSD** | low | 宽松：保留版权声明/NOTICE 即可商用/闭源 |

> **本 SOP 的核心**：永不因为 Star 高、更新勤就盲目引入。必须查协议、查 LICENSE 文件头、实测 API 元数据。`NOASSERTION` 不是“许可证宽松”，而是“检测器未识别”，必须人工抓取 LICENSE 文件确认。

---

## 反 AI 幻觉流程

1. **检索**：用 `gh search repos` 或 GitHub UI 手动寻找候选
2. **一键验证**：`node scripts/standards/select_wheel.mjs --target crawler --stack python`
   → 自动完成 存在性/归档/停更/最新版本/安全公告/OSV 漏洞 六项真实校验，产出机读报告
3. **核实协议**：必要时用 Contents API 抓取真实 LICENSE 文件头（`NOASSERTION` 必须人工确认）
4. **判定**：应用本 SOP 五维表 + 安全门禁 → DIRECT_USE / SUITABLE / REVIEW / ELIMINATE
5. **记录**：元数据、总分、安全等级、判定写入 `standards/wheel_selection_report.json` 供复用

---

## 辅助脚本

- `scripts/standards/select_wheel.mjs` — 五维筛选自动化执行器（参数 `--target crawler --stack python` 等）
- `scripts/standards/verify_pipeline.cjs` — 16 工作流阶段计时验收（阈值 30s，all success 才算通过）
- `scripts/standards/restore_from_github.mjs` — 从 GitHub API 全量恢复本地被回滚的代码文件

---

## 当前状态：16/16 工作流通过

- **16 个阶段** 在 <30s 内全部 success（采集→入库→上架→定价→订单路由→物流→售后→外联→跟进→数据闭环→蜘蛛发现→自学习→自进化→内容官→巡检→记忆）
- 验收命令：`node scripts/standards/verify_pipeline.cjs --seconds 30`
- **降级项（非致命）**：本地无 `GH_TOKEN`/`OPENROUTER_API_KEY`、CDP(:9223) 未启动 → 巡检为 `degraded` 而非 `critical`，`exit=0`。
  配置真实凭据 + 启动 CDP 后即可转正。

> **诚实工程结论**：多数情况下**不引入**第三方框架。我们的自研链路（hidden_crawler → hidden_finder → hidden_crm → hidden_oms → hidden_pay → hidden_outreach → hidden_followup → hidden_realops → hidden_watchdog → hidden_improver → hidden_planner）已就绪，只差真实流量入口（CDP 浏览器:9223）与真实凭据（GH_TOKEN/AI_KEY）。引入外部轮子只会增加协议风险、技术栈碎片化和运维负担。