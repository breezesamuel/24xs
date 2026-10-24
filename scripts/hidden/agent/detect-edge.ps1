# 检测 Edge 可执行文件 + 用户配置，用于重新拉起 CDP
$candidates = @(
  'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
  'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
)
$edge = $null
foreach ($c in $candidates) {
  if (Test-Path $c) { $edge = $c; break }
}
if ($edge) { Write-Output "EDGE_FOUND $edge" } else { Write-Output "EDGE_NOT_FOUND" }

$profile = Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\User Data'
if (Test-Path $profile) {
  Write-Output "PROFILE_EXISTS $profile"
} else {
  Write-Output "PROFILE_MISSING $profile"
}

# 检测 9223 是否监听
$conn = Get-NetTCPConnection -LocalPort 9223 -State Listen -ErrorAction SilentlyContinue
if ($conn) { Write-Output "PORT_9223_LISTENING" } else { Write-Output "PORT_9223_FREE" }