Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonExe = fso.BuildPath(fso.GetParentFolderName(scriptDir), "venv\Scripts\python.exe")

If Not fso.FileExists(pythonExe) Then
  MsgBox "Python executable was not found in the parent venv:" & vbCrLf & pythonExe, 16, "Launch failed"
  WScript.Quit 1
End If

command = """" & pythonExe & """ """ & fso.BuildPath(scriptDir, "web_label.py") & """ --label_video_path="
shell.Run command, 0, False
