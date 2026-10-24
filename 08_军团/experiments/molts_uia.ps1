# Use UIA to read the products list page elements

Add-Type @"
using System;
using System.Runtime.InteropServices;
using System.Diagnostics;
using System.Collections.Generic;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowProc lpEnumFunc, IntPtr lParam);
    public delegate bool EnumWindowProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetClassName(IntPtr hWnd, System.Text.StringBuilder lpClassName, int nMaxCount);
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
$wshell.SendKeys("https://moltspay.com/creators/products{ENTER}")
Start-Sleep -Seconds 4

# Now use UIA to read elements
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes

$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty, 4060)
$win = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)

if ($null -eq $win) {
    Write-Host "Window not found"
    exit 1
}

$walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
$elements = @()

function Walk($el, $depth) {
    if ($null -eq $el -or $depth -gt 8) { return }
    try {
        $name = $el.Current.Name
        $type = $el.Current.ControlType.ProgrammaticName -replace 'ControlType\.', ''
        $id = $el.Current.AutomationId
        $cls = $el.Current.ClassName
        if ($name -or $id -or $cls) {
            $elements += [pscustomobject]@{
                Depth = $depth
                Type = $type
                Name = $name
                AutomationId = $id
                ClassName = $cls
            }
        }
    } catch {}
    $child = $walker.GetFirstChild($el)
    while ($child) {
        Walk $child ($depth + 1)
        try { $child = $walker.GetNextSibling($child) } catch { break }
    }
}

Walk $win 0

$elements | Where-Object { $_.Name -match "pay|link|url|product|price|id|secret|webhook|payout|bank" } | 
    Select-Object Depth, Type, Name, AutomationId, ClassName | Format-Table -AutoSize -Wrap

$elements | Where-Object { $_.Name -like "*http*" -or $_.Name -like "*pay*" } | 
    Select-Object Depth, Type, Name, AutomationId | Format-Table -AutoSize -Wrap

Write-Host "Total elements: $($elements.Count)"