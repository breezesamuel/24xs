# Use known handles from Get-Process to send Ctrl+Enter

$eml1 = "F:\2026\24xs\99_产出\外发草稿\外发_上海夕阳红口腔门_5105.eml"
$eml2 = "F:\2026\24xs\99_产出\外发草稿\外发_上海汇尚口腔_1020.eml"

Add-Type @"
using System;
using System.Runtime.InteropServices;
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

    # Find the Mail process by title
    $procs = Get-Process | Where-Object { $_.MainWindowTitle -match "eml" }
    Write-Host "Found $($procs.Count) Mail processes:"
    $procs | ForEach-Object { Write-Host "  PID $($_.Id): Handle $($_.MainWindowHandle)" }

    foreach ($proc in $procs) {
        $hWnd = $proc.MainWindowHandle
        if (-not [Win32]::IsWindow($hWnd) -or -not [Win32]::IsWindowVisible($hWnd)) { continue }
        Write-Host "Targeting PID $($proc.Id), handle $hWnd"
        [Win32]::ShowWindow($hWnd, 5)
        $ok = [Win32]::SetForegroundWindow($hWnd)
        Write-Host "SetForegroundWindow: $ok"
        Start-Sleep -Seconds 2

        $wshell = New-Object -ComObject WScript.Shell
        $wshell.SendKeys("^{ENTER}")
        Write-Host "Sent Ctrl+Enter to PID $($proc.Id)"
        Start-Sleep -Seconds 3
    }
}

Send-To-Eml "F:\2026\24xs\99_产出\外发草稿\外发_上海夕阳红口腔门_5105.eml"
Send-To-Eml "F:\2026\24xs\99_产出\外发草稿\外发_上海汇尚口腔_1020.eml"
Write-Host "Done"