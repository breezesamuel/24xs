' 静默运行内容分发队列（无窗口）。队列空或 CDP 离线时立即退出，无副作用。
' 由计划任务 AutoOps\Distributor 每 30 分钟调用。
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "F:\2026\24xs"
sh.Run "cmd /c node scripts\hidden\agent\content-distributor.js run-schedule 1 >> autoops\hidden\distributor_task.log 2>&1", 0, False
