# Navigate to payout/bank account settings

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
$wshell.SendKeys("^l")
Start-Sleep -Milliseconds 300
$wshell.SendKeys("https://moltspay.com/creators/settings/payouts{ENTER}")
Write-Host "Navigated to payouts settings"
Start-Sleep -Seconds 3

# The user needs to manually add bank account - just ensure page loads
Write-Host "Payouts page loaded - manual bank account entry required"