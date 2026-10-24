# 一次性部署重试（2026-10-25 21:00 由计划任务触发）
# 目的：Vercel 免费 100 次/日部署配额是滚动窗口，昨晚的消耗陆续老化释放；
#       本脚本每小时可重复执行，成功即自删任务并验证三通道。
$ErrorActionPreference = 'Continue'
$log = 'F:\2026\24xs\autoops\hidden\deploy_retry.log'
"[$(Get-Date -Format u)] retry start" | Add-Content $log

$env:npm_config_cache = 'C:\Windows\Temp\npmcache-retry'
Set-Location 'C:\bingdashan\site'
$tok = (Select-String '^VERCEL_TOKEN=' C:\bingdashan\ai-staff\.env).Line.Split('=',2)[1].Trim()

$out = & npx -y vercel@latest deploy --prod --token=$tok --archive=tgz 2>&1 | Out-String
$out | Add-Content $log

if ($LASTEXITCODE -eq 0 -and $out -match 'Production|https://') {
  "[$(Get-Date -Format u)] DEPLOY OK" | Add-Content $log
  Start-Sleep 40
  $health = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 30 'https://tools.highkingflower.com/api/health').Content
  $aliq   = (Invoke-WebRequest -UseBasicParsing -TimeoutSec 30 'https://tools.highkingflower.com/api/aliq?debug=1').Content
  "health: $health" | Add-Content $log
  "aliq: $aliq" | Add-Content $log
  # 微信通道实测（下单应为 ok:true + code_url，或返回可诊断的新报错）
  try {
    $wx = Invoke-WebRequest -UseBasicParsing -TimeoutSec 30 -Method POST -ContentType 'application/json' -Body '{"plan":"m10","slug":"probe","ref":"P1"}' 'https://tools.highkingflower.com/api/wxpay/create'
    "wxpay: $($wx.Content)" | Add-Content $log
  } catch { "wxpay probe failed: $($_.Exception.Message)" | Add-Content $log }
  # IndexNow 提交核心页收录（密钥文件已随部署上线）
  $ikey = Get-Content 'F:\2026\24xs\autoops\hidden\indexnow.key' -ErrorAction SilentlyContinue
  if (-not $ikey) { $ikey = (Get-ChildItem 'C:\bingdashan\site\*.txt' | Where-Object Name -match '^[0-9a-f]{32}\.txt$' | Select-Object -First 1).BaseName }
  if ($ikey) {
    $pages = @('/','/pricing.html','/arcade/','/subwall.html','/paid.html')
    foreach ($p in $pages) {
      try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 20 "https://api.indexnow.org/indexnow?url=https://tools.highkingflower.com$p&key=$ikey" | Out-Null; "indexnow: $p ok" | Add-Content $log } catch { "indexnow: $p fail" | Add-Content $log }
    }
    "indexnow key: $ikey" | Add-Content $log
  }
  # 成功后删除自身的一次性任务
  schtasks /delete /tn 'AutoOps_DeployRetry' /f | Add-Content $log
} else {
  "[$(Get-Date -Format u)] still limited or failed; task remains for next trigger" | Add-Content $log
}
