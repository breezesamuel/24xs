# 丙大山数字资产平台 - 部署脚本 (PowerShell)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "丙大山数字资产平台 - 部署脚本" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 检查依赖
Write-Host ""
Write-Host "[1/5] 检查依赖..." -ForegroundColor Yellow

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "错误: Node.js 未安装" -ForegroundColor Red
    exit 1
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "错误: Python 未安装" -ForegroundColor Red
    exit 1
}
if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
    Write-Host "错误: Vercel CLI 未安装" -ForegroundColor Red
    Write-Host "请运行: npm i -g vercel" -ForegroundColor Yellow
    exit 1
}
Write-Host "依赖检查通过" -ForegroundColor Green

# 运行验证
Write-Host ""
Write-Host "[2/5] 运行验证..." -ForegroundColor Yellow
python verify.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 验证失败" -ForegroundColor Red
    exit 1
}
Write-Host "验证通过" -ForegroundColor Green

# 检查环境变量
Write-Host ""
Write-Host "[3/5] 检查环境变量..." -ForegroundColor Yellow
$envVars = @("MOLTSPAY_API_KEY", "MOLTSPAY_SECRET", "MOLTSPAY_WEBHOOK_SECRET")
foreach ($var in $envVars) {
    if (-not [Environment]::GetEnvironmentVariable($var)) {
        Write-Host "警告: $var 未设置" -ForegroundColor Yellow
    }
}
Write-Host "环境变量检查完成" -ForegroundColor Green

# 部署
Write-Host ""
Write-Host "[4/5] 部署到 Vercel..." -ForegroundColor Yellow
vercel --prod

# 验证部署
Write-Host ""
Write-Host "[5/5] 验证部署..." -ForegroundColor Yellow
Write-Host "请访问以下 URL 验证部署:" -ForegroundColor Cyan
Write-Host "  - 首页: https://geo-audit-24xs.vercel.app"
Write-Host "  - 健康检查: https://geo-audit-24xs.vercel.app/api/health"
Write-Host "  - API 文档: https://geo-audit-24xs.vercel.app/api-docs.html"
Write-Host "  - 客户门户: https://geo-audit-24xs.vercel.app/portal.html"
Write-Host "  - 系统监控: https://geo-audit-24xs.vercel.app/monitoring.html"
Write-Host "  - 验证中心: https://geo-audit-24xs.vercel.app/verify.html"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "部署完成!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan