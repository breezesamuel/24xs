@echo off
rem 双击此文件 (或以管理员身份运行) 注册 24x7 本地自愈计划任务。
rem 若提示 UAC, 点"是"。
setlocal
cd /d "F:\2026\24xs"

echo === 检查是否管理员 ===
net session >nul 2>&1
if errorlevel 1 (
    echo 需要管理员权限, 正在请求 UAC 提升...
    powershell -Command "Start-Process -FilePath '$PWD\%~nx0' -Verb RunAs"
    goto :end
)

echo 已是管理员, 注册 AutoOps_24x7_SelfHeal (每 30 分钟)...
schtasks /delete /tn "AutoOps_24x7_SelfHeal" /f 2>nul
schtasks /create /tn "AutoOps_24x7_SelfHeal" /tr "node ""F:\2026\24xs\scripts\hidden\agent\run-24x7-selfheal.js""" /sc minute /mo 30 /rl highest /f
if errorlevel 1 (
    echo [ERROR] 注册失败 (看上面 schtasks 输出)
) else (
    echo [OK] 已注册。查询:
    schtasks /query /tn "AutoOps_24x7_SelfHeal" /fo list
    echo.
    echo [测试] 手动触发一次:
    schtasks /run /tn "AutoOps_24x7_SelfHeal"
    timeout /t 8 >nul
    echo.
    echo 最新日志:
    type "F:\2026\24xs\autoops\hidden\24x7_selfheal.log" 2>nul | more
)
:end
endlocal
pause
