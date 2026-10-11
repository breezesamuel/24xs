# AutoOps 全维度缺口分析与补齐报告（第二阶段：真实踩坑修复）

生成时间: 2026-10-11
前一阶段报告: `AUDIT_REPORT.md`（架构层面缺口分析）
本阶段重点: **逐模块深读 + 线上实测**，发现并修复若干致命缺陷。

---

## 一、本轮发现并已修复的缺陷（按严重级）

### P0-1 心跳计费链路完全失效（致命，已修复）
**症状**: `/api/arcade` 生产环境 HTTP 500。
**根因**: `site/api/alipay.js` 中两个变量从未定义：
1. `FREE_SEC`（第 284 行 `dbSet('arc_free_'+ref, FREE_SEC)`）→ 新用户首次请求抛 `ReferenceError: FREE_SEC is not defined`
2. `b`（第 322 行 `friends:b.friends`）→ 缺少 `const b = await arcBonus(ref)`，state/tick 分支均抛 `ReferenceError: b is not defined`
**影响**: 每个新 Arcade 用户 500 → **免费时长永不入账、付费余额永不扣减、邀请奖励不发放**——即产品最核心的心跳计费（唯一真实营收机制）全线失效，且客户端 `.catch(()=>{})` 静默吞掉错误，用户侧表现为"能玩但永远不收不到免费时长"。
**修复**: 定义 `const FREE_SEC = parseInt(process.env.ARCADE_FREE_SEC||'600',10)`；计费前补 `const b=await arcBonus(ref)`。
**线上验证**: 新用户 `/api/arcade?a=state&ref=NEW` → `200 {freeSeconds:600}` ✅；tick → 200 ✅

### P0-2 arcade-extra 路由未重写（已修复）
**症状**: `/api/rank` `/api/reflect` `/api/feedback` 全 404。
**根因**: `vercel.json` 没有对应 rewrites（只重写了 alipay.js 的路由）。
**修复**: 新增 5 条重写：`/api/rank` `/api/reflect` `/api/feedback` `/api/alert` `/api/pending` → `arcade-extra.js`。
**线上验证**: `/api/rank` → 200，`/api/reflect` → 200，`/api/alert` → 200/502（SMTP 层），`/api/pending` → 200 ✅

### P0-3 KV 键前缀契约不匹配（已修复）
**症状**: `/api/rank` 永远 `total:0`；服务端待付单读取不到。
**根因**: `alipay.js` 的 `dbGet/dbSet` 统一加 `bds_` 前缀（`bds_arc_bal_*`），而 `arcade-extra.js` 与 `autoops.js` 扫描的是裸键 `arc_bal_*`。
**修复**: `arcade-extra.js` 统一走 `K(k) = 'bds_' + k`，扫描模式改 `bds_arc_*`。
**线上验证**: `/api/rank` → `total:4`（真实用户数）✅

### P1-1 SMTP 凭据无效（比缺失更隐蔽，已加兜底）
**症状**: `/api/alert` → 502，QQ 返回 `535 Login fail`（本地直连 smtp.qq.com:465 同样 535）。
**根因**: SMTP 授权码错误/失效（15 位，非标准 16 位授权码）。
**影响**: 告警通道静默失效。
**补齐**:
- `/api/alert` 无论 SMTP 成败，都持久化到 KV `bds_alert_*`（兜底通道）
- `/api/autoops.js?a=alerts` 可读回归档
- `hidden_watchdog` 显式探测告警通道，识别 `smtp_broken` 并给出修复指引
- GitHub Actions 任务失败 → GitHub 免费告警邮件（双通道）

### P1-2 未支付订单跨设备流失（已补齐）
**症状**: 用户生成支付单后换设备/清缓存即永久流失。
**补齐**:
- `alipay.js` `/api/arcade` 响应新增只读字段 `pending`（读 `bds_arc_pend_<ref>`，**不触碰任何计费锚点**）
- `arcade-extra.js` 新增 `/api/pending`（需 AUTOOPS_SECRET，支持 set/get/clear）
- `hidden_followup.mjs`：扫描未付订单 → 写服务端待付单（24h 有效）；已支付 ref 自动清除
- **1007 个游戏页面批量注入**"继续支付"横幅（`pendShow`/`pendGo`），幂等 + 全量语法验证通过
**线上验证**: `/api/pending?op=set` → `/api/arcade?a=state&ref=X` 返回 pending → 游戏页含横幅代码 ✅

### P1-3 无静默失败防护（已补齐）
新增 `hidden_watchdog.mjs`，每 tick 巡检 7 项：
心跳新鲜度 / 收银台健康与凭据 / 真实支付转化 / 推广队列积压 / 关键数据文件 / 凭据缺失 / 告警通道有效性。
- 关键故障 → `exit 1` → 编排器透传 → GitHub Actions 发免费告警邮件
- 降级项 → 记录 + 追踪，不轰炸
- 告警去重（同类 6 小时冷却）
- **修复首跑误报**：GitHub Actions 每次全新 checkout，以 `state.json` 缺失判定"首跑"，避免每次误报告警

### P2-1 Planner 是静态写死（已升级）
`hidden_planner.mjs` 原为硬编码 7 条任务。现改为读取真实快照（收银台营收/订单漏斗/线索分级/推广队列）**动态生成按真实瓶颈排序的计划**，并推入 `hidden_tasks.jsonl` 任务队列。

### P2-2 Improver 硬编码规则（已升级）
`hidden_improver.mjs` 现从真实数据学规则：真实支付转化率 → 定价规则；主力套餐 → 推广推荐；AI 生成成功率 → 话术回退；CDP 离线 → 分发受阻告警；线索池结构 → 外呼预算。本地实测学出 5 条规则。

### P2-3 GitHub Actions 工程缺口（已补齐）
| 缺口 | 修复 |
|------|------|
| `contents: read` 导致状态回写 push 失败 | 改 `contents: write` |
| 每次 runner 失忆重启 | `commit_state.sh`（安全回写，push 失败 reset 远端 HEAD 重放，3 次重试） |
| 并发写冲突 | 工作流级 `concurrency: hidden-autoops-state-writer` |
| 公开仓库 60 天无活动 cron 被禁用 | `keepalive.yml`（每 50 天 trivial commit） |
| Secrets 漂移无感知 | `secrets-presence-check.yml`（每周校验，非零退出即告警） |
| **YAML `run:` 值内含 `": "` 导致解析失败**（工作流整体失效，还误触发 push-run 失败） | 改字面块 `run: \|` |

---

## 二、当前系统真实状态

| 环节 | 状态 | 证据 |
|------|------|------|
| 支付宝收银台 | ✅ 真实可用 | `/api/verify` → `PASS (已生成收银台订单)`；`/api/health` app/priv/pub 全 true |
| Arcade 心跳计费 | ✅ **已修复可用** | 新用户 `freeSeconds=600`；tick 正常；邀请奖励正常 |
| 排行榜/心得/反馈/告警 | ✅ 已上线 | `/api/rank` total=4 |
| 待付单挽回 | ✅ 已上线 | LIVETEST / P420252 均返回 pending |
| 30×7 编排 | ✅ Actions 全绿 | run 38126900347：orchestrator success + watchdog success |
| 状态持久化 | ✅ 已生效 | `[commit_state] pushed (attempt 1)` |
| 真实订单/营收 | ⚠️ 2 笔 created / **0 笔 paid / ¥0** | 仅缺流量 |
| CDP 内容分发 | ⏸ 就绪待激活 | drive.js + content-distributor 已实现并同步；缺 CDP(:9223) 浏览器 |
| GH_TOKEN | ❌ 占位 | 爬虫按设计跳过（fail-fast） |
| AI_KEY | ❌ 占位 | 外呼 defer（fail-closed） |
| SMTP | ❌ 无效 | 已降级 KV 兜底 + Actions 邮件 |

---

## 三、剩余可执行项（按 ROI 排序）

1. **启动 CDP 浏览器** → 6 篇推广帖自动分发 → 唯一能把 ¥0 变成收入的杠杆（零代码成本，drive.js 已就绪）
2. **真实 GH_TOKEN** → 激活爬虫/线索管道
3. **真实 AI_KEY** → 激活 AI 外呼与话术生成
4. **修复 SMTP 授权码** → 恢复邮件告警主通道（当前 KV 兜底 + Actions 邮件可用）
5. 阿里云 PM2 部署（需 SSH）

---

## 四、已交付文件清单（本轮）

| 文件 | 作用 |
|------|------|
| `site/api/alipay.js` | **修复 FREE_SEC / b 两个致命未定义变量**；新增只读 pending 字段 |
| `site/api/arcade-extra.js` | KV 前缀契约修复；新增 `/api/pending`；`/api/alert` KV 兜底 |
| `site/api/autoops.js` | 新增 `?a=alerts` / `?a=feedback`；stats 带 alerts |
| `site/vercel.json` | 新增 5 条 arcade-extra 路由重写 |
| `site/arcade/a_*/index.html` | 1007 页注入待付单恢复横幅（幂等，已验证） |
| `scripts/hidden/agent/hidden_watchdog.mjs` | 7 项巡检 + 告警去重 + 退出码透传 |
| `scripts/hidden/agent/hidden_followup.mjs` | 未付订单挽回 |
| `scripts/hidden/agent/hidden_planner.mjs` | 动态规划器 |
| `scripts/hidden/agent/hidden_improver.mjs` | 数据驱动自学习 |
| `scripts/hidden/hidden_orchestrator.mjs` | 集成 followup + watchdog 退出码透传 |
| `scripts/hidden/commit_state.sh` | Actions 状态安全回写 |
| `scripts/hooks/inject_pending.cjs` | 1007 页批量注入器 |
| `.github/workflows/hidden_autoops.yml` | concurrency + 权限修复 + commit 回写 + 独立 watchdog 任务 + YAML 修复 |
| `.github/workflows/keepalive.yml` | 防 cron 被禁用 |
| `.github/workflows/secrets-presence-check.yml` | Secrets 周校验 |
| `promotion/drive.js` | CDP 原语（connect/nav/click/input/wait/screenshot） |
| `promotion/content-distributor.js` | 真实发帖版（6 渠道） |
