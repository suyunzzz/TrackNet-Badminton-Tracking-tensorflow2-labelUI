Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcherPath = fso.BuildPath(scriptDir, "start_web_label.bat")

If Not fso.FileExists(launcherPath) Then
  MsgBox "Launcher was not found:" & vbCrLf & launcherPath, 16, "Launch failed"
  WScript.Quit 1
End If

command = "cmd /c """ & launcherPath & """"
shell.Run command, 1, False
