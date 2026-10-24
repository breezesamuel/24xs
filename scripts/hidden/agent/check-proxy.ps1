$ports = @(7897, 7890, 10809)
$found = $false
foreach ($p in $ports) {
  $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if ($c) { Write-Output "PROXY_UP port=$p pid=$($c[0].OwningProcess)"; $found = $true }
}
if (-not $found) { Write-Output "PROXY_DOWN" }