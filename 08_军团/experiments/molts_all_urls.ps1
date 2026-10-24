# Navigate to products list and webhooks with correct URLs

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
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Clipboard]::SetText("")

function Copy-Page($url, $label) {
    Write-Host "=== $label ==="
    $wshell.SendKeys("^l")
    Start-Sleep -Milliseconds 300
    $wshell.SendKeys("$url{ENTER}")
    Start-Sleep -Seconds 4
    $wshell.SendKeys("^a")
    Start-Sleep -Milliseconds 500
    $wshell.SendKeys("^c")
    Start-Sleep -Milliseconds 500
    $clip = [System.Windows.Forms.Clipboard]::GetText()
    $clip | Out-File "F:\2026\24xs\99_产出\外发草稿\molts_$label.txt" -Encoding UTF8
    Write-Host "$label length: $($clip.Length)"
    $clip | Select-Object -First 300
}

# Try different URL patterns for products list
Copy-Page "https://moltspay.com/creators/products" "products_list"
Copy-Page "https://moltspay.com/creators/products?status=active" "products_active"

# Try different webhooks URLs
Copy-Page "https://moltspay.com/creators/webhooks" "webhooks_v1"
Copy-Page "https://moltspay.com/creators/settings/webhooks" "webhooks_v2"
Copy-Page "https://moltspay.com/creators/developer/webhooks" "webhooks_v3"
Copy-Page "https://moltspay.com/creators/api/webhooks" "webhooks_v4"

# Try different payouts URLs
Copy-Page "https://moltspay.com/creators/payouts" "payouts_v1"
Copy-Page "https://moltspay.com/creators/settings/payouts" "payouts_v2"
Copy-Page "https://moltspay.com/creators/bank-accounts" "payouts_v3"

Write-Host "Done"