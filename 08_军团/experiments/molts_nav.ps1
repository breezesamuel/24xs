# Bring Edge (PID 4060) to front by PID, then send keys
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
        $script:hwnd = $hWnd
        return $false  # stop enumeration
    }
    return $true
}
[Win32]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null

if ($hwnd -eq [IntPtr]::Zero) {
    Write-Host "No visible window for PID $targetPid"
    exit 1
}

Write-Host "Found window: $hwnd"
[Win32]::ShowWindow($hwnd, 5)
$ok = [Win32]::SetForegroundWindow($hwnd)
Write-Host "SetForegroundWindow: $ok"
Start-Sleep -Seconds 1

$wshell = New-Object -ComObject WScript.Shell
$wshell.SendKeys("^l")
Start-Sleep -Milliseconds 500
$wshell.SendKeys("https://moltspay.com/creators/products/new{ENTER}")
Write-Host "Sent navigation keys"