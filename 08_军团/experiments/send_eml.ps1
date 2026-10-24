# Open .eml in default handler, bring to front, send Ctrl+Enter

$eml1 = "F:\2026\24xs\99_产出\外发草稿\外发_上海夕阳红口腔门_5105.eml"
$eml2 = "F:\2026\24xs\99_产出\外发草稿\外发_上海汇尚口腔_1020.eml"

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")] public static extern IntPtr FindWindowEx(IntPtr hwndParent, IntPtr hwndChildAfter, string lpszClass, string lpszWindow);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
"@

function Send-To-Eml {
    param($emlPath)
    Write-Host "Opening $emlPath"
    $proc = Start-Process -FilePath $emlPath -PassThru -WindowStyle Normal
    if (-not $proc) { Write-Host "Failed to start"; return }
    Write-Host "Started process ID: $($proc.Id)"

    # Wait for window to appear (up to 15s)
    $hWnd = [IntPtr]::Zero
    $tries = 0
    while ($hWnd -eq [IntPtr]::Zero -and $tries -lt 30) {
        Start-Sleep -Milliseconds 500
        $hWnd = [Win32]::FindWindow("Chrome_WidgetWin_1", $null)  # Edge uses same class
        # Could also try to find by process ID
        if ($hWnd -eq [IntPtr]::Zero) {
            $all = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
            if ($all) {
                $hWnd = $all.MainWindowHandle
            }
        }
        $tries++
    }

    if ($hWnd -eq [IntPtr]::Zero) {
        Write-Host "Could not find window handle"
        return
    }

    Write-Host "Found window handle: $hWnd"
    [Win32]::ShowWindow($hWnd, 5)  # SW_SHOW
    [Win32]::SetForegroundWindow($hWnd)
    Start-Sleep -Seconds 2

    $wshell = New-Object -ComObject WScript.Shell
    $wshell.SendKeys("^{ENTER}")  # Ctrl+Enter = Send in QQ Mail
    Write-Host "Sent Ctrl+Enter"
    Start-Sleep -Seconds 3
}

Send-To-Eml $eml1
Send-To-Eml $eml2
Write-Host "Done"