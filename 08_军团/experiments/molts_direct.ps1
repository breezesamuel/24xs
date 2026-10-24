# Simple: get Edge main window handle from Get-Process, bring to front, send keys

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Diagnostics;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
}
"@

$edge = Get-Process -Id 4060
if (-not $edge) { Write-Host "Edge PID 4060 not found"; exit 1 }

$hWnd = $edge.MainWindowHandle
Write-Host "Edge MainWindowHandle: $hWnd"

[Win32]::ShowWindow($hWnd, 5)
$ok = [Win32]::SetForegroundWindow($hWnd)
Write-Host "SetForegroundWindow: $ok"
Start-Sleep -Seconds 1

$wshell = New-Object -ComObject WScript.Shell
$wshell.SendKeys("^l")
Start-Sleep -Milliseconds 300
$wshell.SendKeys("https://moltspay.com/creators/products/new{ENTER}")
Write-Host "Navigated to new product page"
Start-Sleep -Seconds 3

# Fill form - tab to each field
$wshell.SendKeys("{TAB}")
Start-Sleep -Milliseconds 200
$wshell.SendKeys("GEO 诊断快检服务")
Start-Sleep -Milliseconds 200
$wshell.SendKeys("{TAB}")
Start-Sleep -Milliseconds 200
$wshell.SendKeys("60000")
Start-Sleep -Milliseconds 200
$wshell.SendKeys("{TAB}")
Start-Sleep -Milliseconds 200
$wshell.SendKeys("AI 搜索可见度审计 + 修复方案 + 复测，7 个工作日交付")
Start-Sleep -Milliseconds 200

# Tab to submit button (usually 5-8 tabs from description)
for($i=0;$i -lt 8;$i++) {
    $wshell.SendKeys("{TAB}")
    Start-Sleep -Milliseconds 150
}
$wshell.SendKeys("{ENTER}")
Write-Host "Submitted product creation"