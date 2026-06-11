Option Explicit

Dim shell, fso, scriptDir, startBat, cmd
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
startBat = scriptDir & "\start_manifest_waitress_dev.bat"

If Not fso.FileExists(startBat) Then
    MsgBox "Startdatei fehlt: " & startBat, 16, "MANIFeST OU"
    Set shell = Nothing
    Set fso = Nothing
    WScript.Quit 1
End If

cmd = "cmd /c """ & startBat & """"
shell.Run cmd, 1, False

Set shell = Nothing
Set fso = Nothing
