@echo off
chcp 65001 >nul
title PHONE 触达拨号器 - 电话/网络电话

set CSV=F:\2026\24xs\99_产出\获客名单\触达队列_A档_2026-09-30.csv
set LOG=F:\2026\24xs\08_军团\experiments\send_log_phone_%date:~-4,4%%date:~-10,2%%date:~-7,2%.csv

echo 公司,行业,渠道,建议方式,ICP分,第1次触达文案,第2次(3天后),第3次(7天后),行动指令,sent_at,status,call_duration,outcome > "%LOG%"

echo.
echo ========================================
echo  电话触达拨号器
echo ========================================
echo.
echo 准备工作：
echo   1. 手机/网络电话(Skype/钉钉/企业微信/飞书电话)已准备好
echo   2. 电话号码需自行从企查查/官网/招聘JD补充（CSV里无电话）
echo   3. 录音/笔记工具准备好
echo.
echo 【开场白模板】已在 CSV 第6列，按公司逐条读
echo.
echo 按任意键开始第一个电话...
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
    echo 【开场白】:
    echo !copy1!
    echo.
    echo 【3天后跟进】:
    echo !copy2!
    echo.
    echo 【7天后跟进】:
    echo !copy3!
    echo.

    echo 请拨打电话，按 [Y] 接通并记录，[N] 无人接听/拒接，[Q] 退出
    choice /C YNQ /M "选择: "
    if errorlevel 3 goto :END
    if errorlevel 2 (
        set /p dur="通话时长(秒，无则0): "
        set /p out="结果(拒绝/回拨/加微信/约会/其他): "
        echo !company!,!industry!,!channel!,!method!,!icp!,"!copy1!","!copy2!","!copy3!","!action!",%date% %time%,no_answer,!dur!,!out! >> "%LOG%"
        continue
    )

    set /p dur="通话时长(秒): "
    set /p out="结果(拒绝/加微信/约会/要资料/其他): "
    echo !company!,!industry!,!channel!,!method!,!icp!,"!copy1!","!copy2!","!copy3!","!action!",%date% %time%,connected,!dur!,!out! >> "%LOG%"
    echo [已记录] !company! - connected - !out!

    echo 是否立即加微信/发邮件跟进？[Y/N]
    choice /C YN /M "选择: "
    if errorlevel 2 continue

    REM 这里可以自动打开微信/邮件发送器
    echo 请手动发送跟进消息...
)

:END
echo.
echo 全部完成！通话日志: %LOG%
pause