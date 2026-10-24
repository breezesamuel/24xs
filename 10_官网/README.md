# 丙大山数字资产平台

## 概述

丙大山数字资产平台是一个商业级数字资产交易系统，提供 100 万+ 真实可验证数字资产的发现、购买、交付、验证和管理功能。

## 核心功能

- **资产发现**: 100 万+ 结构化数字资产，支持全文搜索和分类筛选
- **资产验证**: SHA256 + Merkle Tree 双重验证，确保数据完整性
- **动态定价**: 按套餐、按量、按组合灵活定价
- **订阅管理**: 按月/按年订阅，自动续费，积分额度管理
- **支付闭环**: 支持 MoltsPay、PayPal 等多种支付方式
- **客户门户**: 客户自助管理订阅、查看用量、下载资产
- **管理后台**: 系统监控、客户管理、订单管理、配置管理

## 技术架构

```
前端 (store.html)
    ↓
API 层 (functions/api/*.js)
    ↓
数据层 (11_数据资产/registry_real_verified/)
    ↓
验证层 (Merkle Tree + SHA256)
```

## 快速开始

### 本地开发
```bash
# 安装依赖
npm install

# 运行验证
python verify.py

# 本地预览
npx serve .
```

### 部署
```bash
# 部署到 Vercel
vercel --prod
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| /api/assets | GET | 获取资产列表 |
| /api/search | GET | 全文搜索 |
| /api/verify | POST | 验证资产 Proof |
| /api/pricing | GET | 获取定价信息 |
| /api/purchase | POST | 发起购买 |
| /api/deliver | POST | 获取交付链接 |
| /api/health | GET | 健康检查 |
| /api/portal/profile | GET | 客户档案 |
| /api/portal/credits | GET | 积分信息 |
| /api/portal/purchases | GET | 购买记录 |
| /api/portal/subscription | GET/POST | 订阅管理 |
| /api/admin/dashboard | GET | 管理仪表盘 |
| /api/monitoring | GET | 系统监控 |

## 页面

| 页面 | 描述 |
|------|------|
| / | 数字资产商城 |
| /portal.html | 客户门户 |
| /monitoring.html | 系统监控 |
| /settings.html | 系统配置 |
| /verify.html | 验证中心 |

## 数据资产

- **总资产数**: 1,056,693 条
- **数据大小**: 591 MB
- **Merkle Tree**: 22 层
- **搜索索引**: 450 MB (FTS5)

## 套餐方案

| 套餐 | 月付 | 年付 | 积分额度 |
|------|------|------|----------|
| 入门版 | ¥299 | ¥2,870 | 5,000 |
| 专业版 | ¥999 | ¥9,590 | 15,000 |
| 企业版 | ¥2,999 | ¥28,790 | 50,000 |

## 合规文档

- [服务条款](TERMS_OF_SERVICE.md)
- [隐私政策](PRIVACY_POLICY.md)
- [数据处理协议](DPA.md)

## 支持

- 邮箱: supi24@163.com
- 公司: 上海丙大山智能科技有限公司