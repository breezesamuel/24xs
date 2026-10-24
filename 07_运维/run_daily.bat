@echo off
chcp 65001 > nul
echo [双击运行] AI 交付工厂 - 每日任务
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "F:\2026\24xs\07_运维\run_daily.ps1"
echo.
echo 完成。看板位置：
echo   F:\2026\24xs\99_产出\报告\最新看板.md
echo.
pause
