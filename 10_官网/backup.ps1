# 丙大山数字资产平台 - 数据备份脚本

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupDir = ".\backups"
$zipFile = "$backupDir\backup_$timestamp.zip"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "丙大山数字资产平台 - 数据备份" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 创建备份目录
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

# 定义要备份的文件
$files = @(
    "..\11_数据资产\registry_real_verified\assets_verifiable_1M.jsonl",
    "..\11_数据资产\registry_real_verified\merkle_tree.json",
    "..\11_数据资产\registry_real_verified\quality_report.json",
    "..\11_数据资产\registry_real_verified\pricing_engine.json",
    "..\11_数据资产\registry_real_verified\license_registry.json",
    "..\11_数据资产\registry_real_verified\customer_schema.json",
    "..\11_数据资产\registry_real_verified\analytics_config.json",
    "..\11_数据资产\registry_real_verified\runbooks.json",
    "..\11_数据资产\registry_real_verified\openapi.json",
    "TERMS_OF_SERVICE.md",
    "PRIVACY_POLICY.md",
    "DPA.md",
    "README.md",
    "DEPLOYMENT.md"
)

# 创建临时目录
$tempDir = "$backupDir\temp_$timestamp"
New-Item -ItemType Directory -Path $tempDir | Out-Null

# 复制文件
Write-Host ""
Write-Host "备份文件..." -ForegroundColor Yellow
foreach ($file in $files) {
    if (Test-Path $file) {
        Copy-Item $file $tempDir
        Write-Host "  [OK] $file" -ForegroundColor Green
    } else {
        Write-Host "  [SKIP] $file (不存在)" -ForegroundColor Yellow
    }
}

# 压缩
Write-Host ""
Write-Host "压缩备份..." -ForegroundColor Yellow
Compress-Archive -Path "$tempDir\*" -DestinationPath $zipFile -Force

# 清理临时目录
Remove-Item -Recurse -Force $tempDir

# 显示结果
$size = (Get-Item $zipFile).Length
Write-Host ""
Write-Host "备份完成: $zipFile" -ForegroundColor Green
Write-Host "大小: $([math]::Round($size / 1MB, 2)) MB" -ForegroundColor Green

# 列出所有备份
Write-Host ""
Write-Host "所有备份:" -ForegroundColor Cyan
Get-ChildItem "$backupDir\backup_*.zip" | Sort-Object Name -Descending | ForEach-Object {
    $size = [math]::Round($_.Length / 1MB, 2)
    Write-Host "  $($_.Name) ($size MB)"
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "备份完成!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan