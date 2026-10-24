# -*- coding: utf-8 -*-
"""
install_watchdog_task.py — 注册 7x24 常驻任务

关键设置：
  - ONLOGON + 开机可触发：计划任务在"用户未登录"时也能跑
  - RestartCount / RestartInterval：崩溃后自动重启
  - ExecutionTimeLimit = 0：永不因超时被杀（默认任务是 72h 上限，会被截断）
"""
import subprocess
import sys
from pathlib import Path

TASK_NAME = "24xs_Watchdog"
WATCHDOG = Path(r"F:\2026\24xs\07_运维\watchdog.py")
PY = sys.executable
PIPE_INTERVAL = "21600"  # 6h


def run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def schtasks_fallback():
    """schtasks 需要管理员权限；改用 PowerShell ScheduledTasks 模块（当前用户即可）"""
    import subprocess
    ps = r'''
$ErrorActionPreference = "Stop"
$py  = "%(py)s"
$wd  = "%(wd)s"
$env_ = "WD_PIPELINE_INTERVAL=%(interval)s"
$arg = "/c `"set $env_ && `"$py`" -X utf8 `"$wd`" > NUL 2>&1`""

$a = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $arg -WorkingDirectory (Split-Path -Parent $wd)
# ExecutionTimeLimit = 0 表示永不因运行时长被终止（默认 72h 会截断常驻进程）
$t = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$p = New-ScheduledTaskSettingsSet `
      -AllowStartIfOnBatteries `
      -DontStopIfGoingOnBatteries `
      -StartWhenAvailable `
      -DontStopOnIdleEnd `
      -RestartCount 999 `
      -RestartInterval (New-TimeSpan -Minutes 1) `
      -ExecutionTimeLimit ([TimeSpan]::Zero) `
      -MultipleInstances IgnoreNew
$p.Enabled = $true
$p.WakeToRun = $true

Unregister-ScheduledTask -TaskName "%(name)s" -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName "%(name)s" -Action $a -Trigger $t -Settings $p `
    -Description "24xs 7x24 常驻：官网静态服务 + 公网隧道 + 每日流水线，崩溃自动重启" `
    -Force | Out-Null
Write-Output "registered"
''' % {"py": PY, "wd": WATCHDOG, "interval": PIPE_INTERVAL, "name": TASK_NAME}

    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-Command", ps], capture_output=True, text=True, errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def query() -> None:
    import subprocess
    ps = (f'Get-ScheduledTask -TaskName "{TASK_NAME}" | '
          'Select-Object TaskName, State | Format-List; '
          f'$i = Get-ScheduledTask -TaskName "{TASK_NAME}" | Get-ScheduledTaskInfo; '
          '$i | Select-Object LastRunTime, LastTaskResult, NextRunTime | Format-List; '
          '$s = Get-ScheduledTask -TaskName "{TASK_NAME}"; '
          '"ExecutionTimeLimit=" + $s.Settings.ExecutionTimeLimit; '
          '"RestartCount=" + $s.Settings.RestartCount')
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True, errors="replace")
    print((r.stdout or r.stderr or "").strip())


def main() -> int:
    if not WATCHDOG.exists():
        print(f"[FATAL] watchdog 不存在: {WATCHDOG}")
        return 1

    rc, out = schtasks_fallback()
    print(out.strip())
    if rc != 0:
        print(f"[FAIL] 注册失败 rc={rc}")
        return rc
    print("[ok] 任务已注册")
    query()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
