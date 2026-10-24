# Use the main Edge window, switch tabs with Ctrl+Tab

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Diagnostics;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowProc lpEnumFunc, IntPtr lParam);
    public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
}
"@

$targetPid = 4060
$hwnd = [IntPtr]::Zero

$callback = [Win32+EnumWindowProc] {
    param($hWnd, $lParam)
    if (-not [Win32]::IsWindowVisible($hWnd)) { return $true }
    $pid = 0
    [Win32]::GetWindowThreadProcessId($hWnd, [ref]$pid) | Out-Null
    if ($pid -eq $targetPid) {
        $sb = New-Object System.Text.StringBuilder 512
        [Win32]::GetWindowText($hWnd, $sb, 512) | Out-Null
        if ($sb.ToString() -match "MoltsPay|Edge|Microsoft Edge") {
            $script:hwnd = $hWnd
            return $false
        }
    }
    return $true
}
[Win32]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null

if ($hwnd -eq [IntPtr]::Zero) {
    Write-Host "No window found"
    exit 1
}

Write-Host "Found window: $hwnd"
[Win32]::ShowWindow($hwnd, 5)
$ok = [Win32]::SetForegroundWindow($hwnd)
Write-Host "SetForegroundWindow: $ok"
Start-Sleep -Seconds 1

$wshell = New-Object -ComObject WScript.Shell
# Focus address bar
$wshell.SendKeys("^l")
Start-Sleep -Milliseconds 300
# Navigate
$wshell.SendKeys("https://moltspay.com/creators/products/new{ENTER}")
Write-Host "Navigated"
Start-Sleep -Seconds 3
# Tab through form fields to fill
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
# Try to find and click Create/Save button - usually Tab to it then Enter
for($i=0;$i -lt 10;$i++) {
    $wshell.SendKeys("{TAB}")
    Start-Sleep -Milliseconds 150
}
$wshell.SendKeys("{ENTER}")
Write-Host "Form submitted attempt"