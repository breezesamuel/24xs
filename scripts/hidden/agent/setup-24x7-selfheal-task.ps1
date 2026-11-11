$ROOT = "F:\2026\24xs"
$JS   = "$ROOT\scripts\hidden\agent\run-24x7-selfheal.js"
$LOG  = "$ROOT\autoops\hidden\24x7_selfheal.log"
$TASK = "AutoOps_24x7_SelfHeal"
$INTERVAL_MIN = 30

Write-Host "=== Register 24x7 local self-heal Windows Task ==="
Write-Host "Node: $(node --version 2>&1)"

if (!(Test-Path $JS)) { Write-Host "ERROR: script not found: $JS"; exit 1 }

# syntax self-check
node --check $JS 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Write-Host "WARN: run-24x7-selfheal.js syntax check failed, will still register" }

# remove old task
schtasks /delete /tn $TASK /f 2>$null | Out-Null

$logDir = Split-Path $LOG -Parent
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes $INTERVAL_MIN) -RepetitionDuration (New-TimeSpan -Days 3650)
$action  = New-ScheduledTaskAction -Execute "node" -Argument "`"$JS`"" -WorkingDirectory $ROOT
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TASK -Trigger $trigger -Action $action -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "OK: registered $TASK (every $INTERVAL_MIN min)"
Write-Host "Command: node $JS"
Write-Host "Log: $LOG"

Write-Host ""
Write-Host "Test trigger now..."
Start-ScheduledTask -TaskName $TASK
Start-Sleep -Seconds 8
if (Test-Path $LOG) {
  Write-Host ""
  Write-Host "Latest log (tail 8):"
  Get-Content $LOG -Tail 8
} else {
  Write-Host "Log not created yet (task may still be running): $LOG"
}
