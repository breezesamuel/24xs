# Use rundll32 (worked before) to open .eml, then find window by title

$eml1 = "F:\2026\24xs\99_产出\外发草稿\外发_上海夕阳红口腔门_5105.eml"
$eml2 = "F:\2026\24xs\99_产出\外发草稿\外发_上海汇尚口腔_1020.eml"

Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowProc lpEnumFunc, IntPtr lParam);
    public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
}
"@

function Get-WindowsWithTitle {
    param($pattern)
    $list = @()
    $callback = [Win32+EnumWindowProc] {
        param($hWnd, $lParam)
        if (-not [Win32]::IsWindowVisible($hWnd)) { return $true }
        $sb = New-Object System.Text.StringBuilder 512
        [Win32]::GetWindowText($hWnd, $sb, 512) | Out-Null
        $title = $sb.ToString()
        if ($title -match $pattern) {
            $pid = 0
            [Win32]::GetWindowThreadProcessId($hWnd, [ref]$pid) | Out-Null
            $list += [pscustomobject]@{ Hwnd=$hWnd; Title=$title; Pid=$pid }
        }
        return $true
    }
    [Win32]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
    return $list
}

function Send-To-Eml {
    param($emlPath)
    Write-Host "Opening $emlPath"
    # Use rundll32 which worked earlier
    rundll32.exe url.dll,FileProtocolHandler "$emlPath"
    Start-Sleep -Seconds 6

    $windows = Get-WindowsWithTitle "QQ邮箱|mail\.qq"
    Write-Host "Found $($windows.Count) QQ Mail windows:"
    $windows | ForEach-Object { Write-Host "  PID $($_.Pid): $($_.Title)" }

    $target = $windows | Select-Object -First 1
    if (-not $target) {
        # fallback: any Edge window
        $all = Get-WindowsWithTitle "Microsoft Edge"
        $target = $all | Select-Object -Last 1
    }
    if (-not $target) { Write-Host "No target window"; return }

    Write-Host "Targeting: PID $($target.Pid) - $($target.Title)"
    [Win32]::ShowWindow($target.Hwnd, 5)
    $ok = [Win32]::SetForegroundWindow($target.Hwnd)
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