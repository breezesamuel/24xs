# 重新拉起 Edge + CDP 调试端口（复用默认用户配置，保留登录态）
# 用法:
#   powershell -File launch-edge.ps1                # 直连（默认）
#   powershell -File launch-edge.ps1 -Proxy 127.0.0.1:7897   # 走代理（解锁 X/Reddit/HN）
param(
  [string]$Proxy = ''
)
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$profile = Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\User Data'

$running = Get-Process msedge -ErrorAction SilentlyContinue
if ($running) {
  Write-Output "EDGE_ALREADY_RUNNING pid=$($running[0].Id) (请先完全关闭 Edge 再重跑本脚本以切换代理)"
  exit 0
}

$args = @(
  '--remote-debugging-port=9223',
  '--remote-allow-origins=*',
  "--user-data-dir=$profile",
  '--restore-last-session'
)
if ($Proxy -ne '') {
  $args += "--proxy-server=$Proxy"
  $args += '--proxy-bypass-list=<local>'
  Write-Output "PROXY_ENABLED $Proxy"
} else {
  Write-Output "PROXY_DISABLED direct"
}

Start-Process -FilePath $edge -ArgumentList $args

$ok = $false
for ($i = 0; $i -lt 20; $i++) {
  Start-Sleep -Milliseconds 1000
  try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:9223/json/version' -TimeoutSec 3 -UseBasicParsing
    if ($r.StatusCode -eq 200) { $ok = $true; break }
  } catch {}
}
if ($ok) { Write-Output "CDP_READY" } else { Write-Output "CDP_NOT_READY" }