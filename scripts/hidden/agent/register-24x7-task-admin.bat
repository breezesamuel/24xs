@echo off
rem ============================================================
rem  一键注册 24x7 本地自愈计划任务 (AutoOps_24x7_SelfHeal)
rem  每 30 分钟跑 run-24x7-selfheal.js (本机 24/7 兜底宿主)
rem  需管理员权限 (本脚本自动请求 UAC 提升)。双击运行, 弹 UAC 点"是"。
rem ============================================================
setlocal
cd /d "F:\2026\24xs"

echo === 检查管理员权限 ===
net session >nul 2>&1
if errorlevel 1 (
    echo [INFO] 需要管理员, 正在请求 UAC 提升...
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs -Wait"
    goto :end
)

echo [OK] 已是管理员。注册 AutoOps_24x7_SelfHeal (每 30 分钟)...
schtasks /delete /tn "AutoOps_24x7_SelfHeal" /f 2>nul

schtasks /create /tn "AutoOps_24x7_SelfHeal" /tr "node \"F:\2026\24xs\scripts\hidden\agent\run-24x7-selfheal.js\"" /sc minute /mo 30 /rl limited /f
if errorlevel 1 (
    echo [ERROR] 注册失败, 看上面 schtasks 输出
    goto :end
)

echo [OK] 已注册。查询:
schtasks /query /tn "AutoOps_24x7_SelfHeal" /fo list 2>nul

echo.
echo [测试] 手动触发一次...
schtasks /run /tn "AutoOps_24x7_SelfHeal"
timeout /t 8 /nobreak >nul
echo.
echo === 最新日志 (末 10 行) ===
if exist "F:\2026\24xs\autoops\hidden\24x7_selfheal.log" (
    powershell -NoProfile -Command "Get-Content 'F:\2026\24xs\autoops\hidden\24x7_selfheal.log' -Tail 10"
) else (
    echo (日志尚未生成, 任务可能仍在跑)
)

echo.
echo === 三层 24/7 冗余 ===
echo   云端: Hidden AutoOps 24x7 + 24x7 Self-Heal Trigger + Keepalive
echo   本机: AutoOps_24x7_SelfHeal (此 task, 防 GitHub 整体挂)
echo   注: 笔记本休眠/关机时本机 task 不跑, 云端 3 层仍持续。
:end
endlocal
pause
