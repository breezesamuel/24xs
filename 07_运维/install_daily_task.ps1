# 安装每日自动运行（Windows 计划任务）
# 用法：powershell -ExecutionPolicy Bypass -File "F:\2026\24xs\07_运维\install_daily_task.ps1"
# 卸载：powershell -ExecutionPolicy Bypass -File "F:\2026\24xs\07_运维\install_daily_task.ps1" -Uninstall
param([switch]$Uninstall)

$taskName = "AI_Engine_Daily"
$script   = "F:\2026\24xs\07_运维\run_daily.ps1"

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "已卸载计划任务: $taskName" -ForegroundColor Yellow
    exit 0
}

if (-not (Test-Path -LiteralPath $script)) {
    Write-Error "找不到脚本: $script"
    exit 1
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$script`""

$trigger = New-ScheduledTaskTrigger -Daily -At 8:50am

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

# 优先以 SYSTEM 身份运行（无需登录）；无管理员权限时自动降级为当前用户
$installed = $false
try {
    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
        -Settings $settings -Principal $principal `
        -Description "AI delivery factory: daily dashboard, leads, corpus, simulation" `
        -Force -ErrorAction Stop | Out-Null
    Write-Host "模式: SYSTEM（开机即跑，无需登录）" -ForegroundColor Green
    $installed = $true
} catch {
    try {
        $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -RunLevel Limited
        Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
            -Settings $settings -Principal $principal `
            -Description "AI delivery factory: daily dashboard, leads, corpus, simulation" `
            -Force -ErrorAction Stop | Out-Null
        Write-Host "模式: 当前用户（需该用户已登录）" -ForegroundColor Yellow
        $installed = $true
    } catch {
        Write-Host ""
        Write-Host "[失败] 计划任务注册被系统拒绝（通常需要管理员权限）" -ForegroundColor Red
        Write-Host ""
        Write-Host "改用无需权限的替代方案（二选一）：" -ForegroundColor Yellow
        Write-Host "  1) 双击运行: F:\2026\24xs\07_运维\run_daily.bat"
        Write-Host "  2) 以管理员身份打开 PowerShell 后重跑本脚本："
        Write-Host "     Start-Process powershell -Verb RunAs -ArgumentList '-ExecutionPolicy Bypass -File `"$script`"'"
        exit 2
    }
}

if ($installed) {
    Write-Host ""
    Write-Host "已安装计划任务: $taskName" -ForegroundColor Green
    Write-Host "  执行时间: 每天 08:50"
    Write-Host "  日志位置: F:\2026\24xs\07_运维\daily.log"
    Write-Host "  备份位置: F:\2026\24xs\07_运维\backup\ (保留 30 天)"
    Write-Host ""
    Write-Host "立即测试一次:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName $taskName"
    Write-Host "  Get-Content F:\2026\24xs\07_运维\daily.log -Tail 30"
    Write-Host ""
    Write-Host "卸载任务:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File `"$script`" -Uninstall"
    exit 0
}
