# 每日自动运行脚本
$ErrorActionPreference = "Continue"
$root = "F:\2026\24xs"
$engine = Join-Path $root "01_引擎"
$ops = Join-Path $root "07_运维"
$backup = Join-Path $ops "backup"
$log = Join-Path $ops "daily.log"

New-Item -ItemType Directory -Path $backup -Force | Out-Null

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $log -Value "[$ts] $msg" -Encoding UTF8
}

Log "========== 每日任务开始 =========="

# 1. 环境自检
$py = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $py) {
    Log "[FATAL] 未找到 python，任务中止"
    exit 1
}
Log "Python: $(& python --version 2>&1)"

# 2. 备份数据库（保留最近 30 天）
$db = Join-Path $root "99_产出\_data\factory.sqlite3"
if (Test-Path -LiteralPath $db) {
    $dst = Join-Path $backup ("factory_" + (Get-Date -Format "yyyyMMdd") + ".sqlite3")
    Copy-Item -LiteralPath $db -Destination $dst -Force
    Log "备份完成: $dst"
    Get-ChildItem -Path $backup -Filter "factory_*.sqlite3" |
        Sort-Object LastWriteTime -Descending | Select-Object -Skip 30 |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force; Log "清理旧备份: $($_.Name)" }
} else {
    Log "数据库尚不存在，将在引擎首次运行时创建"
}

# 3. 跑全流程
Push-Location $engine
$env:PYTHONIOENCODING = "utf-8"
$out = & python -X utf8 cli.py all 2>&1
$code = $LASTEXITCODE
Pop-Location

if ($code -eq 0) {
    Log "[OK] 引擎全流程执行成功"
    $out | ForEach-Object { Log "  $_" }
} else {
    Log "[ERROR] 引擎执行失败，退出码 $code"
    $out | ForEach-Object { Log "  $_" }
}

# 3b. 资金栈安全回归测试（涉及资金，必须每天验证 fail-closed 未被破坏）
$secTest = Join-Path $root "08_军团\capital\tests\test_security.py"
if (Test-Path -LiteralPath $secTest) {
    $secOut = & python -X utf8 $secTest 2>&1
    if ($LASTEXITCODE -eq 0) {
        Log "[OK] 资金栈安全测试通过"
    } else {
        Log "[ALERT] 资金栈安全测试失败！可能有人修改了 fail-closed 逻辑，请立即人工检查"
        $secOut | Select-Object -Last 20 | ForEach-Object { Log "  $_" }
    }
}

# 3c. 情报刷新（真实 MCP，失败自动退回离线兜底）
$intel = Join-Path $root "08_军团\intel\lootdrop_intel.py"
if (Test-Path -LiteralPath $intel) {
    Push-Location (Join-Path $root "08_军团")
    $intOut = & python -X utf8 $intel 2>&1
    $intCode = $LASTEXITCODE
    Pop-Location
    if ($intCode -eq 0) {
        Log "[OK] 情报刷新成功"
    } else {
        Log "[WARN] 情报刷新失败（已使用离线兜底数据）"
        $intOut | Select-Object -Last 10 | ForEach-Object { Log "  $_" }
    }
}

# 3d. 官网同步到 Vercel 生产域名（PC 关机后仍可访问）
#     deploy_site.py 内部按 index.html 内容哈希判断，未变化则跳过部署。
$deploy = Join-Path $root "07_运维\deploy_site.py"
if (Test-Path -LiteralPath $deploy) {
    $depOut = & python -X utf8 $deploy 2>&1
    if ($LASTEXITCODE -eq 0) {
        Log "[OK] 官网生产域名已同步"
    } else {
        Log "[WARN] 官网同步失败（线上仍为上一版本）"
        $depOut | Select-Object -Last 6 | ForEach-Object { Log "  $_" }
    }
}

# 4. 统计产出
$prod = Join-Path $root "99_产出"
if (Test-Path -LiteralPath $prod) {
    $files = Get-ChildItem -LiteralPath $prod -Recurse -File -ErrorAction SilentlyContinue
    $size = ($files | Measure-Object -Property Length -Sum).Sum
    Log "产出统计: $($files.Count) 个文件, $([math]::Round($size/1KB,1)) KB"
}

Log "========== 每日任务结束 =========="
