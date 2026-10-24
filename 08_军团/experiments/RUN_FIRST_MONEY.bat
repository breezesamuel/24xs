@echo off
chcp 65001 >nul
title FIRST MONEY 触达总控制器

echo.
echo ============================================================
echo   FIRST MONEY 触达执行器 - 目标：14天内回款 >= 10,000 元
echo ============================================================
echo.
echo 资产就绪：
echo   - 60 条 A档触达队列 (F:\2026\24xs\99_产出\获客名单\触达队列_A档_2026-09-30.csv)
echo   - 3 段零重复文案/人 (私信/邮件/电话三板斧)
echo   - 报价下限：标准版 12万 / 全案 22万
echo   - 实验预算剩余：1000 元
echo.
echo 执行顺序建议：
echo   1. 微信/领英私信 (响应率最高) -> send_wechat.bat
echo   2. 邮件 (正式留痕)         -> send_email.bat
echo   3. 电话 (高意向收割)       -> send_phone.bat
echo.
echo 请先完成准备：
echo   [ ] 微信网页版/领英消息页 已登录，停在输入框
echo   [ ] Gmail/Outlook/Foxmail 已登录，停在写邮件页
echo   [ ] 电话/网络电话 已准备，号码已从企查查/官网补全
echo   [ ] GEO诊断样例PDF 已准备 (99_产出/报告/GEO诊断_样例客户-*.md)
echo   [ ] 报价单模板 已准备 (02_交付物/03_报价单模板.md)
echo.
choice /C 1234 /M "选择启动: [1]私信 [2]邮件 [3]电话 [4]查看日志"
if errorlevel 4 goto :LOGS
if errorlevel 3 start "" "F:\2026\24xs\08_军团\experiments\send_phone.bat" & goto :END
if errorlevel 2 start "" "F:\2026\24xs\08_军团\experiments\send_email.bat" & goto :END
if errorlevel 1 start "" "F:\2026\24xs\08_军团\experiments\send_wechat.bat" & goto :END

:LOGS
echo.
echo ===== 发送日志汇总 =====
dir /b F:\2026\24xs\08_军团\experiments\send_log_*.csv
echo.
type F:\2026\24xs\08_军团\experiments\send_log_wechat_*.csv 2>nul
type F:\2026\24xs\08_军团\experiments\send_log_email_*.csv 2>nul
type F:\2026\24xs\08_军团\experiments\send_log_phone_*.csv 2>nul
pause
goto :END

:END
echo 启动完成。请在弹出的窗口中操作。
pause