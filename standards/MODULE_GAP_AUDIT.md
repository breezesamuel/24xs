# AutoOps 全模块查缺补漏审计 (MODULE GAP AUDIT)

- **审计时间:** 2026-10-12
- **审计范围:** `scripts/hidden/**`（agent + crawler + brain + orchestrator + daemon）、
  `scripts/standards/**`、`.github/workflows/**`、线上 `C:\bingdashan\site\api\**` + `vercel.json`
- **方法:** 静态阅读 + 实测（mock CDP 往返、watchdog 连续运行、payment fail-closed 用例、GitHub/OSV 真实元数据）
- **说明:** 标注 **✅已修复** 的项在本轮已落地（见 `DEVELOPMENT_PROGRESS_REPORT.md` 第 9 节）。

---

## 1. 模块清单

### 1a. 自主体模块 — `scripts/hidden/agent/`

| 文件 | 作用 | 真实/模拟 | 输出 | 风险 |
|---|---|---|---|---|
| `drive.js` | CDP 直连已登录浏览器(:9223)发帖 | Real | — | ✅已修复：4 个未实现方法 + 非法 `Input.enable` + 计时器未 unref |
| `content-distributor.js` | 多渠道路由发帖 + 令牌桶 | Mixed | `failed_posts.json`、schedule | 依赖 `drive.js`（已修）；路径双源 |
| `hidden_guard.mjs` | 写自治策略 JSON | **Sim** | `hidden_guard.json` | 无任何读取方，`enforce_*` 声明为假 |
| `hidden_crawler.mjs`(`../crawler/`) | GitHub/全网采集 | Real | `github_raw.jsonl`、`candidates.jsonl` | 缺 isMain 守卫 |
| `hidden_finder.mjs` | 自动上架 | Sim(本地评分) | `assets_auto_published.jsonl` | mojibake |
| `hidden_leads.mjs` | 线索评分 | Sim(本地) | `leads_auto.jsonl`、`lead_pool.jsonl` | 缺 isMain |
| `hidden_outreach.mjs` | 首次触达 | Mixed | `drafts_auto.jsonl`、`crm_auto.jsonl` | `status:'sent'` 但无投递渠道 |
| `hidden_crm.mjs` | CRM 阶段推进 + 造单 | **Sim** | `crm_auto.jsonl`、`orders_auto.jsonl` | 计时器造 `won`→`HORD-` 单 |
| `hidden_oms.mjs` | 履约 | **Sim** | `orders_auto.jsonl`、`aftersale_auto.jsonl` | 计时器造 shipped/delivered |
| `hidden_pay.mjs` | 多网关支付抽象 | Real | `payments_auto.jsonl`、`payments_reject.jsonl` | ✅已修复：金额/订单号交叉校验 + settleCallback + 拒绝审计 |
| `hidden_realops.mjs` | 收银台桥接 + 获客 | Mixed | `real_metrics.jsonl` 等 | ✅已修复：`posted=true` 仅在分发退出码 0 时 |
| `hidden_followup.mjs` | 未支付跟单 | Real | `followup.jsonl` | isMain 守卫 ✓ |
| `hidden_planner.mjs` | 动态计划 + 执行 | Mixed | `hidden_plan.json`、`planner_actions.jsonl` | isMain 守卫 ✓ |
| `hidden_watchdog.mjs` | 巡检 + 告警 | Real | `health_status.json`、`alert_state.json`、`real_alerts.jsonl` | ✅已修复：告警通道失败不再被遮蔽 + 升级/恢复 + KV 兜底 |
| `hidden_improver.mjs` | 自学习规则 | Sim(本地) | memory/* | 缺 isMain |

### 1b. 编排 / 管线 — `scripts/hidden/`

| 文件 | 作用 | 风险 |
|---|---|---|
| `hidden_orchestrator.mjs` | 顺序执行阶段 | 缺 isMain；仅透传 watchdog 退出码 |
| `hidden_daemon.mjs` | 本地 15min 循环 | CI 未使用 |
| `commit_state.sh` | 状态回写 git | ✅已补 `health_status.json`、`alert_state.json` |

### 1c. 标准/验收 — `scripts/standards/`

| 文件 | 作用 | 风险 |
|---|---|---|
| `verify_pipeline.cjs` | 16 阶段计时验收 | 阶段 13 映射与注释不符；验收会改动真实状态 |
| `select_wheel.mjs` | GitHub/OSV 选型 | ✅已加固：安全门禁（漏洞/公告/最新版本）防幻觉 |
| `restore_from_github.mjs` | 从 GitHub 还原 | 硬编码 ROOT；未捕获 `gh auth token` |

### 1d. 线上边缘 API — `C:\bingdashan\site\api\`

| 文件 | 作用 | 风险 |
|---|---|---|
| `alipay.js` | 支付宝 + 心跳计费 | **P0** 邀请奖励每 tick 重复入账（L310-311） |
| `arcade-extra.js`(live) | 排行/心得/反馈/告警 | ✅已修复 `/api/alert` 未定义 `topic` |
| `arcade-extra.js`(repo 副本) | 同上（陈旧） | ✅已修复 `topic`；KV 前缀仍与 live 分叉 |
| `autoops.js` | 只读运维指标 | ✅已新增 `a=watchdog` / `a=dashboard` 只读端点 |
| `morning-youth.js` | 早安青年小程序 | handler 签名不符 Vercel；未注册路由 |

---

## 2. 优先级缺口（本轮修复状态）

### P0 — 直接阻断营收/论点

1. **✅ `drive.js` 4 个核心方法未实现 → 所有 CDP 发帖必失败。**
   已实现 `_getTargets/_createTarget/_getTargetInfo/_connectWS/_onMessage/_httpGet`，移除非法 `Input.enable`，计时器 `unref`；
   mock CDP 往返实测通过（connect→targets→WS→send→close，进程干净退出）。
   同时修复 **promo 目录第二份副本** `C:\bingdashan\promotion\drive.js`（`/json/list` 的 `id`→`targetId` 映射 + 去掉 `Input.enable`）。
2. **✅ `hidden_realops.mjs` 未校验分发结果即置 `posted=true`。**
   改为仅在子进程退出码 `0` 时置位，否则记 `last_error` + `hidden_realops_post_failed`（fail-closed）。
3. **✅ CI 静默吞掉编排失败**（`hidden_orchestrator.mjs || true`）。改为透出退出码；`if: always()` 步骤仍回写状态。
4. **✅ `payments_auto.jsonl` 未跟踪 → 全新 checkout 触发 watchdog 假 critical。**
   watchdog 关键文件表移除该文件（列为可选），并在 `hidden_pay` CLI 启动时 touch 空文件。
5. **✅ `/api/alert` 未定义 `topic`（live 与 repo 两副本）→ KV 告警兜底全废、watchdog 探测假通过。**
   live + repo 均已补 `const topic`；watchdog 现将 `channel:'unknown'` 视为失败。
6. **✅ 收银台告警通道不可用被遮蔽**：watchdog 现 SMTP→KV 兜底，失败如实记录 `notify_failed`。
7. **待办 `alipay.js` 邀请奖励重复入账（L310-311）。** 每次扣费 tick 都会再次加回 `effBonus` → 有邀请额度的用户可被反复“充值”。**需人工确认后修复**（涉及计费正确性，且无法本地端到端验证）。
8. **待办 `hidden_guard.mjs` 的 `enforce_robots/forbid_direct_write_verified/human_gates_disabled` 是空声明**：无任何模块读取该文件。要么接入爬虫强制，要么改名去掉“已强制”措辞。

### P1 — 可靠性 / 正确性

9. 多个模块缺 `isMain` 守卫（outreach/crm/oms/leads/finder/improver/guard/crawler/realops/orchestrator/daemon）：误 import 即触发生产写入。
10. `hidden_outreach.mjs` / `hidden_planner.mjs` 的 outbound 以 `status:'sent'` / `channel:'auto_sim'` 记录，但无真实投递渠道 → 措辞应改为 `prepared`。
11. `verify_pipeline.cjs` 阶段 13 注释写 `hidden_brain`、实际跑 `hidden_planner`；验收过程会改动真实数据。
12. `restore_from_github.mjs` 硬编码 `F:/2026/24xs`，模块加载即 `execSync('gh auth token')`，缺 `gh` 的机器直接抛错。
13. `morning-youth.js` 导出签名不为 `(req,res)`，且 `vercel.json` 无改写 → 实际不可达。
14. schedule.json 双源：`C:/bingdashan/promotion/schedule.json`（realops 写）与仓库 `promotion/schedule.json`（distributor 写）分叉。
15. `hidden_daemon.mjs` 未被 CI 调用 → `state/heartbeat.json` 从不产生。

### P2 — 打磨

16. 双重 UTF-8 编码乱码：`hidden_finder.mjs`、`hidden_crm.mjs`、`hidden_oms.mjs`。
17. 无根 `package.json`；workflow 的 `npm ci` 形同虚设；Node 20 无全局 `WebSocket`（CI 用 node 20，`drive.js` 会退回 `require('ws')` → CI 中不可用）。
18. `content-distributor.js` 相对/绝对路径混用。
19. `select_wheel.mjs` 候选池硬编码。

---

## 3. “注释/声称 ≠ 事实”清单

| 位置 | 声称 | 事实 |
|---|---|---|
| `hidden_realops.mjs` L17/L20 | 绝不假装已发帖 / 真实闭环 | ✅已修复：现仅在退出码 0 时置 posted |
| `hidden_pay.mjs` L6-12 | 回调→验签→确认 赚钱闭环 | 导出函数此前无调用方；✅已加固 + `settleCallback`（仍需接入 realops/webhook） |
| `hidden_outreach.mjs` L75/L82 | `status:'sent'` | 无投递渠道（`channel:'auto_sim'`） |
| `hidden_guard.mjs` L13-23 | `enforce_robots:true` | 文件只写不读 |
| `hidden_watchdog.mjs` L4-7 | 绝不静默失败 | ✅已修复：告警通道失败不再被 `unknown` 遮蔽 |
| `hidden_crm.mjs`/`hidden_oms.mjs` | 订单路由/物流（“真实” ） | 计时器造单 |
| `verify_pipeline.cjs` L18 vs L46 | 13=hidden_brain | 实跑 hidden_planner |
| `drive.js` L3-5 | 复用已登录浏览器发帖 | ✅已修复（此前 4 方法缺失） |

---

## 4. 结论

- 唯一真实可变现路径（CDP 发帖→流量）此前因 `drive.js` 结构性损坏而 100% 死亡（17/17 `cdp_online:false`）——**本轮已修复并实测**。
- 支付桥（`hidden_pay`）已具备严格 fail-closed 语义（金额/订单号/签名/重放审计），但**仍需接入 realops 或 webhook** 才能形成闭环。
- 收银台真实漏斗仍为空（订单 2 笔、paid=0、营收 ¥0、Arcade 用户 5）；告警通道此前被 `/api/alert` 崩溃 + watchdog 遮蔽双重致盲——**本轮已修复**。
- 剩余 P0：`alipay.js` 邀请奖励重复入账、`hidden_guard` 空声明。
