@echo off
chcp 65001 >nul
title EMAIL 触达发送器 - Gmail/Outlook/Foxmail

set CSV=F:\2026\24xs\99_产出\获客名单\触达队列_A档_2026-09-30.csv
set LOG=F:\2026\24xs\08_军团\experiments\send_log_email_%date:~-4,4%%date:~-10,2%%date:~-7,2%.csv

echo 公司,行业,渠道,建议方式,ICP分,第1次触达文案,第2次(3天后),第3次(7天后),行动指令,sent_at,status > "%LOG%"

echo.
echo ========================================
echo  邮件批量发送器 (Gmail/Outlook/Foxmail)
echo ========================================
echo.
echo 准备工作：
echo   1. 浏览器已打开 https://mail.google.com  或  Outlook 网页版 / Foxmail 客户端
echo   2. 已登录，停在「写邮件」页面
echo   3. 收件人邮箱需自行填入（CSV里无邮箱，需你从官网/企查查补全）
echo.
echo 按任意键开始...
pause >nul

for /f "skip=1 tokens=1-9 delims=," %%a in (%CSV%) do (
    set "company=%%a"
    set "industry=%%b"
    set "channel=%%c"
    set "method=%%d"
    set "icp=%%e"
    set "copy1=%%f"
    set "copy2=%%g"
    set "copy3=%%h"
    set "action=%%i"

    echo.
    echo ----------------------------------------
    echo 公司: !company!
    echo 行业: !industry!
    echo ICP分: !icp!
    echo.
    echo 【邮件正文】:
    echo !copy1!
    echo.

    echo !copy1! | clip

    echo [已复制到剪贴板] 请切换到写邮件页面 -> 主题建议: "!company!｜一份 !industry! 自检表，12 项"
    echo 粘贴正文 -> 填入收件人邮箱 -> 发送
    echo 发送完成后，按 [Y] 记录成功，[N] 跳过，[Q] 退出
    choice /C YNQ /M "选择: "
    if errorlevel 3 goto :END
    if errorlevel 2 (
        echo !company!,!industry!,!channel!,!method!,!icp!,"!copy1!","!copy2!","!copy3!","!action!",%date% %time%,skipped >> "%LOG%"
        continue
    )

    echo !company!,!industry!,!channel!,!method!,!icp!,"!copy1!","!copy2!","!copy3!","!action!",%date% %time%,sent >> "%LOG%"
    echo [已记录] !company! - sent
)

:END
echo.
echo 全部完成！发送日志: %LOG%
pause