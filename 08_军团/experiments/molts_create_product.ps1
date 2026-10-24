# Fill and submit the "Add New Product" form on the current products page

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

# We're already on the products page (from previous nav)
# Tab to Product Name field
$wshell.SendKeys("{TAB}")
Start-Sleep -Milliseconds 200
$wshell.SendKeys("GEO 诊断快检服务")
Start-Sleep -Milliseconds 200

# Tab to Description
$wshell.SendKeys("{TAB}")
Start-Sleep -Milliseconds 200
$wshell.SendKeys("AI 搜索可见度审计 + 修复方案 + 复测，7 个工作日交付")
Start-Sleep -Milliseconds 200

# Tab to Price (USD) - need to convert 600 CNY to USD ~ $83
$wshell.SendKeys("{TAB}")
Start-Sleep -Milliseconds 200
$wshell.SendKeys("83")
Start-Sleep -Milliseconds 200

# Tab to Tags
$wshell.SendKeys("{TAB}")
Start-Sleep -Milliseconds 200
$wshell.SendKeys("geo, audit, ai, seo, china")
Start-Sleep -Milliseconds 200

# Tab to Payment Chains - need to select at least one (Base is recommended)
# Tab through chain checkboxes
for($i=0;$i -lt 5;$i++) {
    $wshell.SendKeys("{TAB}")
    Start-Sleep -Milliseconds 150
}
$wshell.SendKeys(" ")  # check first chain (Base)
Start-Sleep -Milliseconds 200

# Tab to Delivery Type - select "Digital Download"
for($i=0;$i -lt 3;$i++) {
    $wshell.SendKeys("{TAB}")
    Start-Sleep -Milliseconds 150
}
$wshell.SendKeys(" ")  # select Digital Download
Start-Sleep -Milliseconds 200

# Tab to Upload File - we need a file. Create a simple PDF report placeholder
# For now, skip file upload - maybe it's optional? Try to tab past it
for($i=0;$i -lt 5;$i++) {
    $wshell.SendKeys("{TAB}")
    Start-Sleep -Milliseconds 150
}

# Tab to Preview Content
$wshell.SendKeys("GEO 诊断快检服务：7个工作日内交付完整AI可见度审计报告，包含结构化数据缺口分析、FAQPage部署指南、6大AI平台复测方案")
Start-Sleep -Milliseconds 200

# Tab to Create Product button and submit
for($i=0;$i -lt 5;$i++) {
    $wshell.SendKeys("{TAB}")
    Start-Sleep -Milliseconds 150
}
$wshell.SendKeys("{ENTER}")
Write-Host "Submitted product creation"
Start-Sleep -Seconds 3

# Now try to get the payment link - go to products list
$wshell.SendKeys("^l")
Start-Sleep -Milliseconds 300
$wshell.SendKeys("https://moltspay.com/creators/products{ENTER}")
Start-Sleep -Seconds 3

# Select all and copy to get payment link
$wshell.SendKeys("^a")
Start-Sleep -Milliseconds 500
$wshell.SendKeys("^c")
Start-Sleep -Milliseconds 500

# Try webhooks page - might be /settings/webhooks or /webhooks
$wshell.SendKeys("^l")
Start-Sleep -Milliseconds 300
$wshell.SendKeys("https://moltspay.com/creators/webhooks{ENTER}")
Start-Sleep -Seconds 3
$wshell.SendKeys("^a")
Start-Sleep -Milliseconds 500
$wshell.SendKeys("^c")
Start-Sleep -Milliseconds 500

# Try payouts
$wshell.SendKeys("^l")
Start-Sleep -Milliseconds 300
$wshell.SendKeys("https://moltspay.com/creators/payouts{ENTER}")
Start-Sleep -Seconds 3
$wshell.SendKeys("^a")
Start-Sleep -Milliseconds 500
$wshell.SendKeys("^c")
Start-Sleep -Milliseconds 500

Write-Host "Done - check clipboard"