# Navigate to products list and webhooks to extract payment link and signing secret

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
$hWnd = $edge.MainWindowHandle
[Win32]::ShowWindow($hWnd, 5)
[Win32]::SetForegroundWindow($hWnd)
Start-Sleep -Seconds 1

$wshell = New-Object -ComObject WScript.Shell

# 1. Go to products list to get payment link
$wshell.SendKeys("^l")
Start-Sleep -Milliseconds 300
$wshell.SendKeys("https://moltspay.com/creators/products{ENTER}")
Write-Host "Navigated to products list"
Start-Sleep -Seconds 3

# Try to select all and copy (Ctrl+A, Ctrl+C) to get page content
$wshell.SendKeys("^a")
Start-Sleep -Milliseconds 500
$wshell.SendKeys("^c")
Start-Sleep -Milliseconds 500

Write-Host "Copied products page"
Start-Sleep -Seconds 1

# 2. Go to webhooks to get signing secret
$wshell.SendKeys("^l")
Start-Sleep -Milliseconds 300
$wshell.SendKeys("https://moltspay.com/creators/settings/webhooks{ENTER}")
Write-Host "Navigated to webhooks"
Start-Sleep -Seconds 3

$wshell.SendKeys("^a")
Start-Sleep -Milliseconds 500
$wshell.SendKeys("^c")
Start-Sleep -Milliseconds 500

Write-Host "Copied webhooks page"
Start-Sleep -Seconds 1

# Paste clipboard to a file
$wshell.SendKeys("^l")
Start-Sleep -Milliseconds 300
$wshell.SendKeys("notepad{ENTER}")
Start-Sleep -Seconds 1
$wshell.SendKeys("^v")
Start-Sleep -Milliseconds 500
$wshell.SendKeys("^s")
Start-Sleep -Milliseconds 500
$wshell.SendKeys("F:\2026\24xs\99_产出\外发草稿\molts_data.txt{ENTER}")
Start-Sleep -Seconds 1

Write-Host "Saved clipboard to file"