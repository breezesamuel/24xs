# Open .eml via shell execute, bring to front, send Ctrl+Enter

$eml1 = "F:\2026\24xs\99_产出\外发草稿\外发_上海夕阳红口腔门_5105.eml"
$eml2 = "F:\2026\24xs\99_产出\外发草稿\外发_上海汇尚口腔_1020.eml"

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Diagnostics;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("shell32.dll", CharSet=CharSet.Auto)] public static extern IntPtr ShellExecute(IntPtr hwnd, string lpOperation, string lpFile, string lpParameters, string lpDirectory, int nShowCmd);
}
"@

function Send-To-Eml {
    param($emlPath)
    Write-Host "Opening $emlPath via ShellExecute"
    $h = [Win32]::ShellExecute([IntPtr]::Zero, "open", $emlPath, $null, $null, 1)  # SW_SHOWNORMAL = 1
    if ($h -le 32) { Write-Host "ShellExecute failed: $h"; return }

    Write-Host "ShellExecute OK, waiting for window..."
    Start-Sleep -Seconds 5

    # Find the new Edge window (class Chrome_WidgetWin_1)
    $hWnd = [IntPtr]::Zero
    $tries = 0
    while ($hWnd -eq [IntPtr]::Zero -and $tries -lt 40) {
        Start-Sleep -Milliseconds 500
        $hWnd = [Win32]::FindWindow("Chrome_WidgetWin_1", $null)
        $tries++
    }

    if ($hWnd -eq [IntPtr]::Zero) {
        Write-Host "Could not find Edge window"
        return
    }

    Write-Host "Found window: $hWnd"
    [Win32]::ShowWindow($hWnd, 5)
    [Win32]::SetForegroundWindow($hWnd)
    Start-Sleep -Seconds 2

    $wshell = New-Object -ComObject WScript.Shell
    $wshell.SendKeys("^{ENTER}")
    Write-Host "Sent Ctrl+Enter"
    Start-Sleep -Seconds 3
}

Send-To-Eml "F:\2026\24xs\99_产出\外发草稿\外发_上海夕阳红口腔门_5105.eml"
Send-To-Eml "F:\2026\24xs\99_产出\外发草稿\外发_上海汇尚口腔_1020.eml"
Write-Host "Done"