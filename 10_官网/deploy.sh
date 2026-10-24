#!/bin/bash
# 丙大山数字资产平台 - 部署脚本

set -e

echo "=========================================="
echo "丙大山数字资产平台 - 部署脚本"
echo "=========================================="

# 检查依赖
echo ""
echo "[1/5] 检查依赖..."
if ! command -v node &> /dev/null; then
    echo "错误: Node.js 未安装"
    exit 1
fi
if ! command -v python &> /dev/null; then
    echo "错误: Python 未安装"
    exit 1
fi
if ! command -v vercel &> /dev/null; then
    echo "错误: Vercel CLI 未安装"
    echo "请运行: npm i -g vercel"
    exit 1
fi
echo "依赖检查通过"

# 运行验证
echo ""
echo "[2/5] 运行验证..."
python verify.py
if [ $? -ne 0 ]; then
    echo "错误: 验证失败"
    exit 1
fi
echo "验证通过"

# 检查环境变量
echo ""
echo "[3/5] 检查环境变量..."
if [ -z "$MOLTSPAY_API_KEY" ]; then
    echo "警告: MOLTSPAY_API_KEY 未设置"
fi
if [ -z "$MOLTSPAY_SECRET" ]; then
    echo "警告: MOLTSPAY_SECRET 未设置"
fi
if [ -z "$MOLTSPAY_WEBHOOK_SECRET" ]; then
    echo "警告: MOLTSPAY_WEBHOOK_SECRET 未设置"
fi
echo "环境变量检查完成"

# 部署
echo ""
echo "[4/5] 部署到 Vercel..."
vercel --prod

# 验证部署
echo ""
echo "[5/5] 验证部署..."
echo "请访问以下 URL 验证部署:"
echo "  - 首页: https://geo-audit-24xs.vercel.app"
echo "  - 健康检查: https://geo-audit-24xs.vercel.app/api/health"
echo "  - API 文档: https://geo-audit-24xs.vercel.app/api-docs.html"
echo "  - 客户门户: https://geo-audit-24xs.vercel.app/portal.html"
echo "  - 系统监控: https://geo-audit-24xs.vercel.app/monitoring.html"
echo "  - 验证中心: https://geo-audit-24xs.vercel.app/verify.html"

echo ""
echo "=========================================="
echo "部署完成!"
echo "=========================================="