# 阿里云 tools-cn 支付宝 40002 (isv.invalid-signature) 防复发 SOP

## 现象
`https://tools-cn.highkingflower.com/api/order` 查单返回
`{"code":"40002","sub":"isv.invalid-signature"}`（而 Vercel 主站正常返回 40004 ACQ.TRADE_NOT_EXIST）。
**后果：阿里云域无法建单/验签 → 客户在 tools-cn 付款会"收钱不认账"（假开通/丢钱）。**

## 根因（两层）
1. 阿里云 `/etc/bingdashan-cn.env` 用 **文件形式**密钥：
   `ALIPAY_MERCHANT_PRIVATE_KEY_FILE=/etc/bingdashan-cn/alipay_priv.pem`
   `ALIPAY_ALIPAY_PUBLIC_KEY_FILE=/etc/bingdashan-cn/alipay_pub.pem`
   直接往 `ALIPAY_MERCHANT_PRIVATE_KEY=` 填 base64 是**无效的**（服务只读 `_FILE`）。
2. 更关键：`/etc/bingdashan-cn/` 里的 PEM 必须是**支付宝开放平台 app_id `2021006197622702` 下已登记配对**的密钥。
   之前该目录里是**另一对**自配对正确但**未在平台登记**的密钥 → 网关侧验签失败 40002。
   （`DEPLOY-40002.md` 早记录过同类根因：登记的公钥必须与代码私钥配对。）

## 修复 SOP（已执行一次，密钥源 = Vercel 同款平台登记密钥）
```bash
# 1. 把 Vercel 同款 base64 DER 密钥传到阿里云 /tmp
#    应用私钥:  C:\Users\46012\Documents\支付宝开放平台密钥工具\应用私钥RSA2048-...txt  → /tmp/alipay_priv.b64
#    支付宝公钥: C:\Users\46012\Documents\支付宝开放平台密钥工具\支付宝公钥.txt        → /tmp/alipay_pub.b64
scp ... /tmp/alipay_priv.b64 /tmp/alipay_pub.b64   (alias aliyun = 8.155.53.12)

# 2. 用 _fix_cn_keypair.sh: base64 DER → 标准 PEM, 写回 /etc/bingdashan-cn/
ssh aliyun "bash /tmp/_fixkp.sh"

# 3. 重启 + 验证查单变 40004
systemctl restart bingdashan-cn
curl -s -X POST https://tools-cn.highkingflower.com/api/order \
     -H 'Content-Type: application/json' -d '{"out_trade_no":"PAIRTEST"}'
# 期望 sub=ACQ.TRADE_NOT_EXIST (40004), 不再是 isv.invalid-signature (40002)
```

## 验证（双活对齐）
`python scripts/hidden/agent/_verify_cn_fullloop.py` → tools-cn 与 Vercel 全链路全绿
（建单/查单/权益/订阅墙/配置 全部一致）。

## 自动监控（防复发）
- `.github/workflows/storefront_integrity.yml` 每天 02:00 UTC 跑
  "Verify dual-active Alipay signature (Vercel + Aliyun tools-cn)" 探针：
  任一端点查到 `isv.invalid-signature` → 该 job 失败 → GitHub 告警邮件。
- 本地复现：`python scripts/hidden/agent/_verify_sig_fix.py`（对比两域签名码）。

## 关联服务（收款到账自动开通）
- `bd-pay-email-watch.timer`（active）：定期扫支付宝到账邮件 → 严格匹配 → 自动开通。
- `bd-audit.service`：审计门，发现"钱漏/端点漏网"时故意 exit 2 报警。**修复后已全绿（门禁通过 exit 0）**。
- `bd-reconcile.service`：三账本对账门（站点账本/闭环镜像/漏斗），**修复后 exit 0**。
- `bingdashan-cn.service`：storefront 主服务（node 直跑 ops/site_cn_server.mjs，非 docker）。

## 追加修复（2026-11-09 深挖）
### A. 订阅墙权益持久化（收钱不认账 → 已修）
- 根因：`subwall.js` 的 dget/dset 只走 KV/Supabase，CN 两者都没配 → 客户付款后
  `activate()` 返回 store_failed，权益写不进（钱收了没开通）。
- 修复：`subwall.js` 加 `FILE_STORE_DIR` file-store 回退，且修正 dget/dset（无远端存储时也走 file fallback）。
- 实证：CN `activate → 文件落库 → HTTP 读回 subscribed=true`。
- 公共 `subscribe`/`extend` 已改 fail-closed（堵白嫖漏洞）。

### B. 账实分离：钱漏清零 + 收费墙 100% 覆盖（审计/对账门 → 全绿）
- **钱漏**：`mvklhggzx6pz0`（¥1 trial, `channel=manual, needProof=true, proofImage=null`）
  是**无付款凭证的未核实 manual 单** → 诚实 void 为 `void_test/paid=false`。
  ⚠️ 关键：账本是**分片**的（`data/shards/*.json` 为源，`db.json` 是 merge 快照），
  只改 `db.json` 会被运行进程下次写覆盖还原 → 必须**改 shards + 重启主服务 `bingdashan.service`**。
  脚本：`scripts/hidden/agent/_void_and_restart.sh`。
- **收费墙真漏网**：45 个内部运营端点（revenue-ops/anomaly/partner-recruit/ledger/dataq/hw/...）
  未登记 → 加进 `core/paywall.js` 的 `FLOW_OPS`（诚实分类为 运营/管理端点，非客户付费工具）。
  脚本：`scripts/hidden/agent/_register_all_ops.sh`。
  注意 `paywall.js` 是阿里云盘上文件（不在 24xs 仓库），改动直接在 ECS 上做并备份。
- 结果：`bd-audit`（无钱漏/无墙漏网 exit 0）+ `bd-reconcile`（三账本对齐 exit 0）全 success。

### C. 收款通道形态（设计如此，非 bug）
- 审计报 "可用=manual 风险=⚠高风险"：AI-staff 的 `/v1/*` 主系统确实用「个人收款码+邮件核账」，
  商户网关代码已就绪但走的是 storefront（tools/tools-cn 的支付宝）。这是诚实标记，不掩盖。

## 追加修复（2026-11-10 深挖）
### D. Vercel PayPal/pay 5 端点 500 (FUNCTION_INVOCATION_FAILED) → 已修
- 根因链:
  1. 项目根 `package.json` 是 `type: commonjs`，handler (`api/paypal/*.js`) 用 ESM `import`
     → `@vercel/node` 构建时 CJS 上下文 `require` 不到 ESM 依赖 → 函数加载即崩 = 500。
  2. 更深一层: `lib/_lib/package.json` 有 `type: module`，即使 handler 改 CJS `require`，
     `require('./lib/_lib/paypal.js')` 拿到**空对象** (ESM 不走 module.exports) → `new PayPalGateway` 抛。
- 修复: `_lib` 全模块 (plans/paypal/pending/mailer) + 5 个 handler 全转 **CJS** (`require`/`module.exports`)，
  **删除 `lib/_lib/package.json`** (让整树统一 CJS)，凭证缺失改 **503 fail-closed** (非 500 崩溃)。
- 结果: 5 端点全 4xx/200 干净；`/api/paypal/order` 真打 PayPal API (422=sandbox 测试, 网关可达)。

### E. 阿里云 CN /dashboard 404 → 已修 (隐蔽 const bug)
- 现象: CN `/dashboard` 404 而 Vercel 200；加 rewrite 后仍 404。
- 真因 (深挖): 请求 handler 里 `pathname` 是 `const`，我的 rewrite `pathname = "/dashboard.html"`
  → `TypeError: Assignment to constant variable` → 被 `catch{}` **静默吞掉** → 永远 404。
  日志在 `/www/wwwlogs/bingdashan-cn.error.log` (非 journald, `StandardOutput=append:...`)。
- 修复: 用**局部变量** `resolvedPath` 传给 `serveStatic`；缺 `dashboard.html` 也补传。
- 教训: 静默 `catch{}` + `const` 重名 组合最坑；改前先看运行日志真因。

### F. Hidden AutoOps security-lint (actionlint+shellcheck+codeql/zizmor) → 已修
- `storefront_integrity.yml` 里 `probe_wall`/`probe_entitle` 的 `local ref="...$(date...)"`
  触发 shellcheck **SC2155** (declare-and-assign 分离) → actionlint 把 warning 当 fatal → job 失败。
- 修复: `local ref` 与 `ref="...$(...)"` 拆成两行。已触发 run 验证通过。
- 注: zizmor 的 `unpinned-uses` (keepalive/secrets-presence 用 @v4 未锁 hash) 是 **note/warning 级, 非 fatal**, 可后续再锁。

## 最终健康总扫
`python scripts/hidden/agent/_sig_sweep.py`（双活查单签名 40004）
`bash scripts/hidden/agent/_final_sweep.sh`（在阿里云跑：双活收款+订阅墙+账实审计+全服务）
`.github/workflows/storefront_integrity.yml`（每天 02:00 UTC 双活 5 探针自动监控）
