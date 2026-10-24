# bds-js-sdk

丙大山数字资产平台官方 JavaScript/TypeScript SDK。

## 安装
```bash
npm install bds-js-sdk
# 或
yarn add bds-js-sdk
```

## 快速开始

### TypeScript / ES Modules
```typescript
import { BDSClient } from "bds-js-sdk";

const client = new BDSClient({
  apiKey: "sk_live_xxxxxxxx",
  baseUrl: "https://geo-audit-24xs.vercel.app"
});

// 搜索资产
const assets = await client.searchAssets({ q: "采购方画像", type: "采购方画像", limit: 10 });
console.log(assets);

// 购买
const purchase = await client.purchase({ asset_id: "V-20261003-001234", qty: 1 });
console.log(purchase.checkout_url); // 跳转支付

// 验证
const verify = await client.verifyProof("...", { name: "xxx" });
console.log(verify.match);
```

### CommonJS / Node.js
```javascript
const { BDSClient } = require("bds-js-sdk");

const client = new BDSClient({ apiKey: "sk_live_xxx" });
```

### 浏览器 (CDN)
```html
<script src="https://unpkg.com/bds-js-sdk@1.0.0/dist/index.js"></script>
<script>
  const client = new BDSClient({ apiKey: "sk_live_xxx" });
</script>
```

## API 参考

### 实例化
```typescript
const client = new BDSClient({
  apiKey: "sk_live_xxxxxxxx",     // 必填
  baseUrl: "https://geo-audit-24xs.vercel.app",  // 可选
  timeout: 30000,                 // 可选，默认 30s
  maxRetries: 3                   // 可选，默认 3
});
```

### 资产发现
```typescript
// 列表
const list = await client.listAssets(100, 0);

// 搜索
const results = await client.searchAssets({ q: "采购方画像", type: "采购方画像", limit: 20 });
```

### 验证
```typescript
// 单条验证
const verify = await client.verifyProof(proof, data);

// 链式变体验证
const verify = await client.verifyChain(proof, parentProof, variantIndex);
```

### 定价与购买
```typescript
// 查询价格
const pricing = await client.getPricing({ asset_type: "采购方画像", qty: 10, bundle: "ccgp_full_buyer" });

// 发起购买
const purchase = await client.purchase({ asset_id: "V-20261003-001234", qty: 1 });
// 跳转 purchase.checkout_url

// 查询交付
const delivery = await client.checkDelivery(purchaseId, txnId);
```

### 客户门户
```typescript
const profile = await client.getProfile();
const credits = await client.getCredits();
const purchases = await client.listPurchases(1, 20);
const apiKeys = await client.listApiKeys();
const newKey = await client.createApiKey("Production", ["read", "search", "verify"], 60);
await client.revokeApiKey("KEY-xxx");
const invoices = await client.listInvoices();
const usage = await client.getUsage(30);
await client.upgradeTier("professional");
```

### 管理后台 (需 admin token)
```typescript
const dashboard = await client.adminDashboard();
const customers = await client.adminListCustomers(1, 20, "acme");
await client.adminSuspendCustomer("CUST-xxx");
await client.adminCreditCustomer("CUST-xxx", 5000);
```

### 监控
```typescript
const health = await client.healthCheck();
const metrics = await client.getMetrics();
const alerts = await client.getAlerts();
```

## 类型定义
完整类型定义见 `dist/index.d.ts`。

## 错误处理
所有方法在网络错误、HTTP 非 2xx、超时时抛出 Error。建议统一 try-catch。

## 许可证
Proprietary - 丙大山智能科技所有权利保留。
