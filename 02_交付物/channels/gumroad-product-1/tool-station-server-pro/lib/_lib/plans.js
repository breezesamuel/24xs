// Subscription plans (mirror of Python plans.py)
export const SUBSCRIPTION_PLANS = {
  basic: {
    name: "基础体验卡",
    price: 1.0,
    durationDays: 1,
    features: ["AI知识库基础访问", "有限次数客服咨询", "10个查询/日", "基础报告功能"],
    description: "1元体验AI知识库，体验价值后再决策",
    isPopular: false,
  },
  professional: {
    name: "专业进阶卡",
    price: 9.9,
    durationDays: 30,
    features: ["AI知识库完整访问", "7x24h AI客服咨询", "无限次查询", "高级报告分析", "工具使用权限", "数据导出功能"],
    description: "专业版：30天无限使用，持续赋能企业",
    isPopular: true,
  },
  flagship: {
    name: "旗舰年度卡",
    price: 99.0,
    durationDays: 365,
    features: ["所有功能解锁", "VIP优先客服通道", "合作伙伴分佣权", "数据白标导出", "自定义知识库搭建", "专属客服经理", "多端同步访问"],
    description: "旗舰版：年度订阅最高性价比，企业首选",
    isPopular: false,
  },
};

export const CURRENCY = "CNY";