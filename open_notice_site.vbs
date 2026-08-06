Option Explicit

' Starts both local services from this script's folder, then opens notices.
' Keep this file pure ASCII because WSH uses the system ANSI codepage.

Dim shell, fso, baseDir, pythonExe, noticeServer, newsServer
Dim noticeCommand, newsCommand, url

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

baseDir = fso.GetParentFolderName(WScript.ScriptFullName)
noticeServer = fso.BuildPath(baseDir, "notice_server.py")
newsServer = fso.BuildPath(baseDir, "news_server.py")
url = "http://127.0.0.1:8765/"

pythonExe = fso.BuildPath(baseDir, ".venv\Scripts\pythonw.exe")
If Not fso.FileExists(pythonExe) Then
    pythonExe = fso.BuildPath(baseDir, ".venv\Scripts\python.exe")
End If
If Not fso.FileExists(pythonExe) Then
    pythonExe = "pythonw.exe"
End If

If Not fso.FileExists(noticeServer) Or Not fso.FileExists(newsServer) Then
    MsgBox "notice_server.py or news_server.py not found in:" & vbCrLf & baseDir, vbCritical, "CQU Notice Hub"
    WScript.Quit 1
End If

noticeCommand = """" & pythonExe & """ """ & noticeServer & """"
newsCommand = """" & pythonExe & """ """ & newsServer & """"
shell.CurrentDirectory = baseDir
shell.Run noticeCommand, 0, False
shell.Run newsCommand, 0, False

WScript.Sleep 1500
shell.Run url, 1, False
