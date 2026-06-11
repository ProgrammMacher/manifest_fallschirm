Option Explicit

Dim shell, fso, scriptDir, entryPy, entryPyc, setupBat, startBat
Dim runtimeHome, activeVenvDir, activePython, activePythonw
Dim entry, pythonwPath, secretsPath, programData, installedSecretsPath

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

entryPy = scriptDir & "\manifest_launcher.py"
entryPyc = scriptDir & "\manifest_launcher.pyc"
setupBat = scriptDir & "\setup_start_manifest.bat"
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

activeVenvDir = runtimeHome & "\venv"
activePython = activeVenvDir & "\Scripts\python.exe"
activePythonw = activeVenvDir & "\Scripts\pythonw.exe"

pythonwPath = ""
If IsVenvHealthy(activePython) And fso.FileExists(activePythonw) Then
	pythonwPath = activePythonw
Else
	If fso.FileExists(setupBat) Then
		shell.Run "cmd /c """ & setupBat & """", 1, True
	End If

	If IsVenvHealthy(activePython) And fso.FileExists(activePythonw) Then
		pythonwPath = activePythonw
	Else
		MsgBox "Keine funktionsfaehige virtuelle Umgebung gefunden. Bitte setup_start_manifest.bat ausfuehren.", 16, "MANIFeST OU"
		Set shell = Nothing
		Set fso = Nothing
		WScript.Quit 1
	End If
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

shell.Run """" & pythonwPath & """ """ & entry & """", 0, False
Set shell = Nothing
Set fso = Nothing

Function IsVenvHealthy(pythonPath)
	Dim command, exitCode
	IsVenvHealthy = False

	If Not fso.FileExists(pythonPath) Then
		Exit Function
	End If

	command = Chr(34) & pythonPath & Chr(34) & " --version"
	exitCode = shell.Run(command, 0, True)
	If exitCode = 0 Then
		IsVenvHealthy = True
	End If
End Function

Function GetDefaultSecretsPath()
	GetDefaultSecretsPath = scriptDir & "\data\secrets\auth_config.json"
End Function