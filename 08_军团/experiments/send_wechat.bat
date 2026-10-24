@echo off
chcp 65001 >nul
title WECHAT 触达发送器 - 微信/脉脉/领英私信

set CSV=F:\2026\24xs\99_产出\获客名单\触达队列_A档_2026-09-30.csv
set LOG=F:\2026\24xs\08_军团\experiments\send_log_wechat_%date:~-4,4%%date:~-10,2%%date:~-7,2%.csv

echo 公司,行业,渠道,建议方式,ICP分,第1次触达文案,第2次(3天后),第3次(7天后),行动指令,sent_at,status > "%LOG%"

echo.
echo ========================================
echo  微信/脉脉/领英私信 批量发送器
echo ========================================
echo.
echo 准备工作：
echo   1. 浏览器已打开 https://mp.weixin.qq.com  或  https://www.linkedin.com/messaging
echo   2. 已扫码登录，停在「发消息」输入框页面
echo   3. 准备好 Ctrl+V 粘贴、Enter 发送
echo.
echo 按任意键开始第一条...
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
    echo 建议方式: !method!
    echo ICP分: !icp!
    echo.
    echo 【第1次文案】:
    echo !copy1!
    echo.

    REM 把文案写入剪贴板
    echo !copy1! | clip

    echo [已复制到剪贴板] 请切换到浏览器聊天框 -> Ctrl+V -> Enter 发送
    echo 发送完成后，按 [Y] 记录成功，[N] 跳过，[Q] 退出
    choice /C YNQ /M "选择: "
    if errorlevel 3 goto :END
    if errorlevel 2 (
        echo !company!,!industry!,!channel!,!method!,!icp!,"!copy1!","!copy2!","!copy3!","!action!",%date% %time%,skipped >> "%LOG%"
        continue
    )

    REM 记录成功
    echo !company!,!industry!,!channel!,!method!,!icp!,"!copy1!","!copy2!","!copy3!","!action!",%date% %time%,sent >> "%LOG%"
    echo [已记录] !company! - sent
)

:END
echo.
echo 全部完成！发送日志: %LOG%
pause