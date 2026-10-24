# Use known window handle from Get-Process to send Ctrl+Enter

$eml1 = "F:\2026\24xs\99_产出\外发草稿\外发_上海夕阳红口腔门_5105.eml"
$eml2 = "F:\2026\24xs\99_产出\外发草稿\外发_上海汇尚口腔_1020.eml"

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Diagnostics;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool IsWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
}
"@

function Send-To-Eml {
    param($emlPath)
    Write-Host "Opening $emlPath"
    rundll32.exe url.dll,FileProtocolHandler "$emlPath"
    Start-Sleep -Seconds 5

    # Find the Mail process by title pattern
    $proc = Get-Process | Where-Object { $_.MainWindowTitle -match "eml.*邮件" } | Select-Object -First 1
    if (-not $proc) { Write-Host "No Mail process found"; return }

    $hWnd = $proc.MainWindowHandle
    Write-Host "Found process PID $($proc.Id), handle $hWnd"

    if (-not [Win32]::IsWindow($hWnd)) { Write-Host "Invalid handle"; return }
    if (-not [Win32]::IsWindowVisible($hWnd)) { Write-Host "Window not visible"; return }

    [Win32]::ShowWindow($hWnd, 5)
    $ok = [Win32]::SetForegroundWindow($hWnd)
    Write-Host "SetForegroundWindow: $ok"
    Start-Sleep -Seconds 2

    $wshell = New-Object -ComObject WScript.Shell
    $wshell.SendKeys("^{ENTER}")
    Write-Host "Sent Ctrl+Enter"
    Start-Sleep -Seconds 3
}

Send-To-Eml "F:\2026\24xs\99_产出\外发草稿\外发_上海夕阳红口腔门_5105.eml"
Send-To-Eml "F:\2026\24xs\99_产出\外发草稿\外发_上海汇尚口腔_1020.eml"
Write-Host "Done"