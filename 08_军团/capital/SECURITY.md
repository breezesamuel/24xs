# 资金自动化安全边界

本模块涉及真实资金与税务，**默认全部关闭**。本文说明哪些动作可自动执行、哪些必须人工介入，以及为什么。

## 一、当前状态：全部 fail-closed

| 能力 | 状态 | 说明 |
|---|---|---|
| 生成支付链接 | 可用（占位配置） | `create_order` 仅在配置真实商户密钥后才可发起真实收款 |
| 支付宝回调验签 | 已实现 | RSA2 验签 + form 解码，验签失败一律拒绝 |
| 微信回调验签 | 已实现 | 需 `wechatpay_public_key_enc`；未配置则**拒绝所有回调** |
| 微信资源解密 | 已实现 | APIv3 `AEAD_AES_256_GCM`，需 32 字节 APIv3 密钥 |
| 报税申报提交 | **未接入** | `submit_if_approved()` 永远返回 `False`，须人工在电子税务局申报 |
| 分红计算 | 可用 | 产出**待审草稿**，不自动批准、不自动付款 |
| 分红付款 | **默认拒绝** | 需 `approved_by_human=True` + `approval_evidence` + 双人审批 |
| 银企直连 EBICS | **未实现** | 明确返回失败，不静默降级 |

> 报税与付款属于法定行为。代码在未接入官方接口并完成核验前，一律拒绝执行，而不是"假装成功"。
> 旧实现 `submit_if_approved()` 在未申报时返回 `True`，会把未完成的申报记成已完成 —— 该问题已修复。

## 二、必须人工介入的动作

以下动作**每次执行都需要当次人工确认**，不接受"全托管"授权：

1. **资金流出**：付款、分红、提现、退款
2. **税务申报**：增值税、企业所得税、个税代扣代缴
3. **开票**：增值税专用发票 / 发票作废与红冲
4. **任何登录态操作**：需要验证码、扫码、2FA 的站点
5. **对外批量发送**：邮件、微信、电话（受《个人信息保护法》《广告法》约束）

技术性、本地可逆、无资金影响的动作（跑流水线、生成报告、跑测试）可以无人值守。

## 三、双人授权的实现

`DividendDistributor.approve()` 要求两名**不同的外部自然人**：

- 系统账号被拒绝：`SYSTEM_APPROVER_BLOCKLIST = {ceo, cfo, admin, system, bot, test, me}`
- 同一审批人重复审批不计数
- `execute()` 额外要求 `approval_evidence`（审批留痕，如工单号、邮件、会议纪要编号）

原实现在代码里直接 `approve(plan_id, "CEO")` + `approve(plan_id, "CFO")` 模拟双签 —— 这等于没有授权，已移除。

## 四、敏感数据处理

**禁止硬编码**：姓名、证件号、银行账号、手机号、邮箱授权码、纳税人识别号、私钥。

| 数据 | 存放位置 | 生成方式 |
|---|---|---|
| 支付配置 | `payment_config.enc` | `python -X utf8 08_军团\capital\payment_gateway.py` |
| 主密钥 | `08_军团\capital/.master.key` | 自动生成，权限仅当前用户 |
| 股东名册 | `shareholders.enc` | 照 `shareholders.template.json` 填写后加密 |
| 纳税主体 | `entity_profile.json` | 照 `entity_profile.template.json` 填写 |

`.gitignore` 已排除 `.master.key`、`*.enc`、`entity_profile.json`、`capital_state.json`。

密钥加载优先级：显式参数 > 环境变量 `PAYMENT_MASTER_KEY` > `.master.key` 文件。

> 之前 `__main__` 用了 `"my_master_password"` 且写相对路径，与运行时读取的 `.master.key` 不一致，导致
> `cryptography.exceptions.InvalidToken`；相对路径还把文件写到了进程 CWD 而非模块目录。已修复并有回归测试。

## 五、账本正确性

`CapitalAllocator.available()` 的口径：

```
可用余额 = 桶分配额 - Σ max(allocated_cny, spent_cny)   # status ∉ {cancelled, reinvested}
```

- 取 `max(allocated, spent)`：分配即锁定额度，防止对同一笔预算反复 `allocate`
- 关闭实验（`completed`/`stopped`）**不退还**额度，防止重复投放
- `cancelled` 释放额度
- `reinvested` 不再扣减，因 `_maybe_reinvest()` 已把本金加回本桶

旧实现只统计 `status == "active"` 且只看 `spent_cny`，导致实验桶在两笔实验各花 1000 元后仍显示 4000 可用 —— 正是 First Money 被误跑两次的原因。修复后实验桶正确显示 `0`。

## 六、回归测试

```
python -X utf8 08_军团\capital\tests\test_security.py
```

20 项，覆盖：源码敏感信息扫描、报税 fail-closed、分红 fail-closed、
双人授权、回调验签拒绝、账本口径、密钥一致性。

## 七、接手真实配置前的检查清单

- [ ] 已在商户平台开通支付，拿到真实 `app_id` / 商户号 / 私钥 / 平台公钥
- [ ] `notify_url` 是公网 HTTPS 可达，回调日志已打开
- [ ] 回调处理已做**幂等**（按 `order_id` 去重），避免重复入账
- [ ] `shareholders.enc` 已由两名不同自然人核对
- [ ] 报税仍由持证会计在电子税务局完成
- [ ] 首次真实付款用小额验证（如 1 元），核对回单后再放量
