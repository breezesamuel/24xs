# 推送重试（GitHub 直连间歇被重置时的兜底）：成功即自删任务
$log = 'F:\2026\24xs\autoops\hidden\push_retry.log'
Set-Location 'F:\2026\24xs'
$tok = (& "C:\Program Files\GitHub CLI\gh.exe" auth token) 2>$null
if (-not $tok) { "[$(Get-Date -Format u)] no gh token" | Add-Content $log; exit 1 }
$out = & git push "https://x-access-token:$tok@github.com/breezesamuel/24xs.git" HEAD:main 2>&1 | Out-String
$out | Add-Content $log
if ($out -match 'main -> main|Everything up-to-date|up to date') {
  "[$(Get-Date -Format u)] PUSH OK — self-delete" | Add-Content $log
  schtasks /delete /tn 'AutoOps_PushRetry' /f | Add-Content $log
} else {
  "[$(Get-Date -Format u)] push failed; retry next trigger" | Add-Content $log
}
