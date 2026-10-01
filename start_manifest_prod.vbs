Option Explicit

Dim shell, fso, scriptDir, entryPy, entryPyc, startBat
Dim runtimeHome, activePythonw
Dim entry, secretsPath, programData, installedSecretsPath

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

entryPy = scriptDir & "\manifest_launcher.py"
entryPyc = scriptDir & "\manifest_launcher.pyc"
startBat = scriptDir & "\start_manifest_prod.bat"

entry = entryPy
If fso.FileExists(entryPyc) Then
	entry = entryPyc
End If

runtimeHome = scriptDir
programData = shell.ExpandEnvironmentStrings("%PROGRAMDATA%")
If Trim(programData) = "" Then
	programData = "C:\ProgramData"
End If
installedSecretsPath = programData & "\ManifestFallschirm\secrets\auth_config.json"

If fso.FileExists(installedSecretsPath) Then
	runtimeHome = programData & "\ManifestFallschirm"
	shell.Environment("Process").Item("MANIFEST_RUNTIME_HOME") = runtimeHome
	shell.Environment("Process").Item("MANIFEST_SECRETS_PATH") = installedSecretsPath
	secretsPath = installedSecretsPath
Else
	secretsPath = GetDefaultSecretsPath()
	shell.Environment("Process").Item("MANIFEST_RUNTIME_HOME") = runtimeHome
	shell.Environment("Process").Item("MANIFEST_SECRETS_PATH") = secretsPath
End If

' Die mitgelieferte Runtime enthaelt bereits alle Abhaengigkeiten; es wird
' absichtlich keine venv unter Program Files angelegt oder benoetigt.
activePythonw = scriptDir & "\runtime\python\pythonw.exe"
If Not fso.FileExists(activePythonw) Then
	MsgBox "Die mitgelieferte Python-Runtime fehlt: " & activePythonw & vbCrLf & "Bitte MANIFeST OU neu installieren.", 16, "MANIFeST OU"
	Set shell = Nothing
	Set fso = Nothing
	WScript.Quit 1
End If

If Not fso.FileExists(secretsPath) Then
	If fso.FileExists(startBat) Then
		' Einmaliger Fallback mit sichtbarer Konsole fuer Lizenz-/Secrets-Einrichtung.
		shell.Run "cmd /c """ & startBat & """", 1, False
		Set shell = Nothing
		Set fso = Nothing
		WScript.Quit 0
	Else
		MsgBox "Secrets-Datei fehlt: " & secretsPath & vbCrLf & "Bitte start_manifest_prod.bat ausfuehren.", 16, "MANIFeST OU"
		Set shell = Nothing
		Set fso = Nothing
		WScript.Quit 1
	End If
End If

shell.Run """" & activePythonw & """ """ & entry & """", 0, False
Set shell = Nothing
Set fso = Nothing

Function GetDefaultSecretsPath()
	GetDefaultSecretsPath = scriptDir & "\data\secrets\auth_config.json"
End Function