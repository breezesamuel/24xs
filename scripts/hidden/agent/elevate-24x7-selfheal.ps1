$ROOT = "F:\2026\24xs"
$PS1  = "$ROOT\scripts\hidden\agent\setup-24x7-selfheal-task.ps1"
# 请求管理员权限重新执行注册脚本 (UAC)
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$p  = New-Object Security.Principal.WindowsPrincipal($id)
$admin = $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Host "Current admin = $admin"
if ($admin) {
    Write-Host "Already elevated, running registration directly..."
    powershell -NoProfile -ExecutionPolicy Bypass -File $PS1
} else {
    Write-Host "Re-launching as Administrator (UAC prompt will appear)..."
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile","-ExecutionPolicy","Bypass","-File",$PS1 -Wait
    Write-Host "Elevated registration attempted. Verify task:"
    schtasks /query /tn "AutoOps_24x7_SelfHeal" /fo list
}
