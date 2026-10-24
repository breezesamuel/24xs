# Navigate to webhooks page and fill webhook form

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
$wshell.SendKeys("https://moltspay.com/creators/settings/webhooks{ENTER}")
Write-Host "Navigated to webhooks settings"
Start-Sleep -Seconds 3

# Fill webhook form
$wshell = New-Object -ComObject WScript.Shell
# Tab to URL field
$wshell.SendKeys("{TAB}")
Start-Sleep -Milliseconds 200
$wshell.SendKeys("https://geo-audit-24xs.vercel.app/api/webhook/moltspay")
Start-Sleep -Milliseconds 200

# Tab to events checkboxes (payment.succeeded)
for($i=0;$i -lt 5;$i++) {
    $wshell.SendKeys("{TAB}")
    Start-Sleep -Milliseconds 150
}
$wshell.SendKeys(" ")  # check checkbox
Start-Sleep -Milliseconds 200

# Tab to next event (payment.failed)
$wshell.SendKeys("{TAB}")
Start-Sleep -Milliseconds 150
$wshell.SendKeys(" ")
Start-Sleep -Milliseconds 200

# Tab to save button
for($i=0;$i -lt 5;$i++) {
    $wshell.SendKeys("{TAB}")
    Start-Sleep -Milliseconds 150
}
$wshell.SendKeys("{ENTER}")
Write-Host "Webhook saved attempt"