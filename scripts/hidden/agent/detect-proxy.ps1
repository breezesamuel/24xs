# 排查本机代理：系统代理设置 + 常见代理端口监听
Write-Output "=== Windows Internet Settings ==="
$reg = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
try {
  $s = Get-ItemProperty -Path $reg -ErrorAction Stop
  Write-Output ("ProxyEnable=" + $s.ProxyEnable)
  Write-Output ("ProxyServer=" + $s.ProxyServer)
  Write-Output ("AutoConfigURL=" + $s.AutoConfigURL)
} catch { Write-Output "READ_FAILED" }

Write-Output "=== Common proxy ports listening ==="
$ports = @(7890, 7891, 7897, 1080, 1081, 10808, 10809, 8118, 8888, 2080, 20171, 33210, 9910)
foreach ($p in $ports) {
  $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if ($c) {
    $proc = (Get-Process -Id $c[0].OwningProcess -ErrorAction SilentlyContinue).ProcessName
    Write-Output "LISTEN port=$p pid=$($c[0].OwningProcess) proc=$proc"
  }
}

Write-Output "=== Proxy-ish processes ==="
$names = @('clash','clash-verge','Clash for Windows','v2ray','v2rayN','xray','sing-box','nekoray','shadowsocks','ssr','trojan','mihomo','verge')
foreach ($n in $names) {
  $p = Get-Process -Name $n -ErrorAction SilentlyContinue
  if ($p) { Write-Output "RUNNING $n pid=$($p[0].Id)" }
}
Write-Output "DONE"