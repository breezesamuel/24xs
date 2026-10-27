$ROOT = "F:\2026\24xs"
$JS = "$ROOT\scripts\hidden\agent\run-distributor-hidden.js"
$LOG = "$ROOT\autoops\hidden\distributor_task.log"
$TASK_NAME = "AutoOps_Distributor"

Write-Host "=== 设置 24xs 内容分发计划任务 ==="
Write-Host "Node: $(node --version 2>&1)"

if (!(Test-Path $JS)) {
    Write-Host "ERROR: Script not found: $JS"
    exit 1
}

# 删除旧任务
schtasks /delete /tn "$TASK_NAME" /f 2>$null

# 创建目录
$logDir = Split-Path $LOG -Parent
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

# 创建任务
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 30)
$action = New-ScheduledTaskAction -Execute "node" -Argument "`"$JS`"" -WorkingDirectory $ROOT
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

Register-ScheduledTask -TaskName $TASK_NAME -Trigger $trigger -Action $action -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "OK: Task created: $TASK_NAME"
Write-Host "Command: node $JS"
Write-Host "Log: $LOG"
Write-Host "Trigger: Every 30 minutes, starting in 1 minute"

# 手动触发
Write-Host "`nTesting..."
Start-ScheduledTask -TaskName $TASK_NAME
Start-Sleep -Seconds 5

if (Test-Path $LOG) {
    Write-Host "`nLog content:"
    Get-Content $LOG -Tail 10
}
