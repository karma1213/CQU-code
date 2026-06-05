Option Explicit

Dim shell, baseDir, pythonExe, server, command, url

Set shell = CreateObject("WScript.Shell")
baseDir = "D:\Program Files\cherry\DS Agent"
pythonExe = "C:\Users\karma\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
server = baseDir & "\news_server.py"
url = "http://127.0.0.1:8766/"

command = """" & pythonExe & """ """ & server & """"
shell.CurrentDirectory = baseDir
shell.Run command, 0, False

WScript.Sleep 1500
shell.Run url, 1, False
