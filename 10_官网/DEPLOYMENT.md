# 丙大山数字资产平台 - 部署检查清单

## 1. 环境准备

- [ ] Node.js 18+ 已安装
- [ ] Python 3.9+ 已安装
- [ ] Vercel CLI 已安装 (`npm i -g vercel`)
- [ ] Git 已安装

## 2. 环境变量配置

在 Vercel 项目设置中配置以下环境变量：

```env
MOLTSPAY_API_KEY=your_api_key
MOLTSPAY_SECRET=your_secret
MOLTSPAY_WEBHOOK_SECRET=your_webhook_secret
PAYPAL_CLIENT_ID=your_client_id
PAYPAL_SECRET=your_secret
ALIPAY_ACCOUNT=your_alipay_account
```

## 3. 部署步骤

### 3.1 本地测试
```bash
python verify.py
```

### 3.2 部署到 Vercel
```bash
vercel --prod
```

### 3.3 验证部署
- [ ] 访问 https://geo-audit-24xs.vercel.app
- [ ] 检查 /api/health 返回正常
- [ ] 检查 /api/assets 返回数据
- [ ] 检查 /api/search 搜索功能
- [ ] 检查 /api/pricing 定价功能

## 4. 数据验证

- [ ] Merkle Tree 根哈希正确
- [ ] 资产数量 > 1,000,000
- [ ] 质量报告 8/8 通过
- [ ] 搜索索引正常

## 5. 支付链路

- [ ] MoltsPay Webhook 端点可访问
- [ ] 支付成功回调正常
- [ ] 订阅续费回调正常
- [ ] 支付失败处理正常

## 6. 监控告警

- [ ] 健康检查端点正常
- [ ] 错误率 < 1%
- [ ] 响应时间 < 500ms
- [ ] 积分不足告警正常

## 7. 安全

- [ ] 所有 API 需要认证
- [ ] Webhook 签名验证正常
- [ ] 敏感信息不在代码中
- [ ] HTTPS 强制启用

## 8. 备份

- [ ] 数据库每日备份
- [ ] 配置文件版本控制
- [ ] 灾难恢复计划就绪