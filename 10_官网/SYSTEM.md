# 丙大山数字资产平台 - 系统文档

## 1. 系统概述

丙大山数字资产平台是一个商业级数字资产交易系统，提供 100 万+ 真实可验证数字资产的发现、购买、交付、验证和管理功能。

## 2. 核心指标

| 指标 | 数值 |
|------|------|
| 总资产数 | 1,056,693 条 |
| 数据大小 | 591 MB |
| Merkle Tree 层数 | 22 |
| 搜索索引大小 | 450 MB |
| API 端点数 | 31 |
| 支持套餐 | 3 档 |

## 3. 技术栈

- **前端**: HTML5 + CSS3 + JavaScript (ES6+)
- **后端**: Cloudflare Pages Functions (Node.js)
- **数据库**: JSONL + SQLite FTS5
- **验证**: SHA256 + Merkle Tree
- **支付**: MoltsPay / PayPal
- **部署**: Vercel

## 4. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层                                │
│  store.html │ portal.html │ monitoring.html │ settings.html │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        API 层                                │
│  assets │ search │ verify │ pricing │ purchase │ deliver    │
│  customer │ analytics │ monitoring │ admin │ portal         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        业务层                                │
│  entitlements │ webhook_queue │ notification │ rate_limit │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        数据层                                │
│  assets_verifiable_1M.jsonl │ merkle_tree.json │ customer   │
│  pricing_engine.json │ license_registry.json │ analytics   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                        验证层                                │
│  SHA256 │ Merkle Tree │ FTS5 Index                         │
└─────────────────────────────────────────────────────────────┘
```

## 5. 数据模型

### 5.1 资产 (Asset)

```json
{
  "asset_id": "V-20261003-001234",
  "type": "采购方画像",
  "name": "采购方画像_上海市医疗器械采购中心",
  "source": "11_数据资产/ccgp_production.db:buyer_profile",
  "proof": "sha256_hash",
  "proof_type": "sha256",
  "price_cny_ref": 500.0,
  "price_cny_floor": 100.0,
  "deliverable": "采购方全维度画像",
  "tags": ["ccgp", "buyer_profile", "high_value"]
}
```

### 5.2 客户 (Customer)

```json
{
  "customer_id": "CUST-xxx",
  "email": "user@example.com",
  "company_name": "xxx公司",
  "tier": "professional",
  "status": "active",
  "billing_cycle": "monthly",
  "included_credits": 15000,
  "used_this_month": 0,
  "credit_balance": 15000,
  "renews_at": "2026-11-07T00:00:00.000Z"
}
```

### 5.3 订单 (Purchase)

```json
{
  "purchase_id": "P-xxx",
  "customer_id": "CUST-xxx",
  "asset_ids": ["V-xxx"],
  "amount_cny": 500.0,
  "status": "completed",
  "created_at": "2026-10-07T00:00:00.000Z"
}
```

## 6. API 设计原则

- **RESTful**: 使用标准 HTTP 方法
- **JSON**: 所有请求/响应使用 JSON 格式
- **认证**: 通过 Header 传递客户 ID
- **错误处理**: 统一的错误响应格式
- **分页**: 支持 limit/offset 分页

## 7. 安全机制

- **身份验证**: 所有 API 需要客户 ID
- **Webhook 签名**: HMAC-SHA256 验证
- **限流**: Token Bucket + Sliding Window
- **数据验证**: SHA256 + Merkle Tree 双重验证
- **HTTPS**: 强制 HTTPS 通信

## 8. 监控告警

- **健康检查**: /api/health
- **错误率**: < 1%
- **响应时间**: < 500ms
- **积分不足**: 自动告警
- **订阅到期**: 提前 3 天提醒

## 9. 部署流程

1. 本地验证: `python verify.py`
2. 部署: `vercel --prod`
3. 验证部署: 访问各页面检查
4. 监控: 定期检查 /api/health

## 10. 维护计划

- **每日**: 数据备份
- **每周**: 质量检查
- **每月**: 安全审计
- **每季**: 性能优化