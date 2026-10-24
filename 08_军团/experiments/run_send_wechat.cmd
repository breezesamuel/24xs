@echo off
chcp 65001 >nul
title FIRST_MONEY 微信触达 - 15条实名公司
cd /d "%~dp0"
if not exist send_logs mkdir send_logs
echo ==========================================================
echo  微信触达发送器 - 已剔除占位，只发 15 条实名公司
echo  流程：每条自动复制第1次文案到剪贴板
echo        切到聊天框 Ctrl+V 然后 Enter 发送
echo        回来按 Y=已发 N=跳过 Q=退出
echo ==========================================================
echo.
python -X utf8 sender_helper.py --csv "F:\2026\24xs\99_产出\获客名单\触达队列_A档_可发_15条_20260930.csv" --channel wechat
echo.
echo 发送结束。日志目录: %~dp0send_logs
pause
