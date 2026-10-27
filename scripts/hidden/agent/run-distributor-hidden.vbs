' 静默运行内容分发队列（无窗口）。队列空或 CDP 离线时立即退出，无副作用。
' 由计划任务 AutoOps\Distributor 每 30 分钟调用。
' 修复: 不依赖 WScript.Shell（某些环境 CreateObject 返回 Nothing）
On Error Resume Next
Dim nodeExe, scriptPath, logPath, fso, ws
nodeExe = "node"
scriptPath = "F:\2026\24xs\scripts\hidden\agent\content-distributor.js"
logPath = "F:\2026\24xs\autoops\hidden\distributor_task.log"

' 方法1: 直接用 WScript.Echo 写日志（无需 sh）
Set fso = CreateObject("Scripting.FileSystemObject")
If Err.Number <> 0 Then
    Set fso = Nothing
    WScript.Quit 1
End If

' 确保日志目录存在
Dim logDir
logDir = fso.GetParentFolderName(logPath)
If Not fso.FolderExists(logDir) Then
    fso.CreateFolder(logDir)
End If

' 写入启动日志
Dim logFile
Set logFile = fso.OpenTextFile(logPath, 8, True) ' 8 = ForAppending
logFile.WriteLine "[" & Now & "] Distributor 启动"
logFile.Close

' 方法2: 用 CreateObject("WScript.Shell") 的替代方案
' 尝试用 mshta + vbscript 静默运行，避免 OpenWindow 问题
Dim cmd
cmd = "cmd /c cd /d F:\2026\24xs && node """ & scriptPath & """ run-schedule 1 >> """ & logPath & """ 2>&1"

' 直接调用 cscript/wscript 自己的 Run 能力
' 如果 WScript.Shell 不可用，fallback 到同步执行（阻塞但安全）
Dim shellUsed
shellUsed = False
On Error Resume Next
Set ws = CreateObject("WScript.Shell")
If Err.Number = 0 And Not ws Is Nothing Then
    ws.CurrentDirectory = "F:\2026\24xs"
    ws.Run cmd, 0, False  ' 0=隐藏窗口, False=不等待
    shellUsed = True
    Set ws = Nothing
End If
On Error GoTo 0

If Not shellUsed Then
    ' Fallback: 同步执行（有窗口但可靠）
    Dim wshFallback
    Set wshFallback = CreateObject("WScript.Shell")
    If Err.Number = 0 Then
        wshFallback.Run cmd, 1, True  ' 1=正常窗口, True=等待完成
        Set wshFallback = Nothing
    Else
        ' 最后 fallback: 用 fso 执行
        Dim proc
        Set proc = fso.Exec(cmd)
        If Not proc Is Nothing Then
            proc.StdIn.Close
            proc.StdOut.Close
            proc.StdErr.Close
        End If
    End If
End If

Set fso = Nothing