# 丙大山数字资产平台 - 更新日志

## [2.0.0] - 2026-10-07

### 新增功能

#### 前端页面
- **store.html** - 数字资产商城，支持筛选、搜索、购买
- **portal.html** - 客户门户，管理订阅、查看用量、下载资产
- **monitoring.html** - 系统监控，实时查看服务状态
- **settings.html** - 系统配置，修改定价参数
- **verify.html** - 验证中心，一键运行所有测试
- **api-docs.html** - API 文档，完整的接口说明
- **architecture.html** - 系统架构，可视化架构图
- **dashboard.html** - 管理仪表盘，查看运营数据
- **admin.html** - 系统管理，客户管理、系统操作
- **setup.html** - 快速开始，新手引导
- **pricing.html** - 定价方案，套餐对比
- **about.html** - 关于我们，公司介绍

#### API 端点
- **assets.js** - 资产列表
- **search.js** - 全文搜索
- **search_enhanced.js** - 增强搜索
- **verify.js** - 资产验证
- **validation.js** - 数据验证
- **pricing.js** - 定价引擎
- **purchase.js** - 购买流程
- **deliver.js** - 资产交付
- **webhook_moltspay.js** - 支付回调
- **webhook_retry.js** - 重试管理
- **customer.js** - 客户管理
- **portal.js** - 客户门户
- **portal_subscription.js** - 订阅管理
- **analytics.js** - 数据分析
- **monitoring.js** - 系统监控
- **admin.js** - 管理后台
- **config.js** - 系统配置
- **export.js** - 数据导出
- **batch.js** - 批量操作
- **invoice.js** - 发票管理
- **notifications.js** - 通知系统
- **quality.js** - 质量检查
- **recommendations.js** - 推荐系统
- **suggestions.js** - 搜索建议
- **asset_stats.js** - 资产统计
- **health.js** - 健康检查
- **system.js** - 系统状态
- **backup.js** - 数据备份

#### 脚本工具
- **verify.py** - 综合验证
- **validate.py** - 数据验证
- **check.py** - 数据检查
- **monitor.py** - 监控告警
- **alert.py** - 告警脚本
- **backup.py** - 数据备份
- **deploy.sh** - 部署脚本 (Bash)
- **deploy.ps1** - 部署脚本 (PowerShell)
- **backup.ps1** - 备份脚本 (PowerShell)

#### 文档
- **README.md** - 项目说明
- **DEPLOYMENT.md** - 部署检查清单
- **SYSTEM.md** - 系统文档
- **INDEX.md** - 文件索引
- **CHANGELOG.md** - 更新日志
- **TERMS_OF_SERVICE.md** - 服务条款
- **PRIVACY_POLICY.md** - 隐私政策
- **DPA.md** - 数据处理协议

### 核心数据
- 总资产数: 1,056,693 条
- 数据大小: 591 MB
- Merkle Tree 层数: 22
- 搜索索引大小: 450 MB

### 技术栈
- 前端: HTML5 + CSS3 + JavaScript (ES6+)
- 后端: Cloudflare Pages Functions (Node.js)
- 数据库: JSONL + SQLite FTS5
- 验证: SHA256 + Merkle Tree
- 支付: MoltsPay / PayPal
- 部署: Vercel

### 已知问题
- 无

### 下一步计划
- [ ] 添加更多支付方式
- [ ] 支持多语言
- [ ] 添加数据分析面板
- [ ] 优化搜索性能
- [ ] 添加更多资产类型

## [1.0.0] - 2026-10-01

### 初始版本
- 基础商城功能
- 资产展示和搜索
- 基础购买流程
- 客户管理
- 支付集成