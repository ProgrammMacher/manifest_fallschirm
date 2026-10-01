#define MyAppName "MANIFeST OU"
#define MyAppVersion "1.2.0"
#define MyAppPublisher "MANIFeST"
#define MyAppExeName "start_manifest_prod.vbs"
#ifndef StageDir
  #define StageDir "..\\..\\build\\inno_stage"
#endif

[Setup]
AppId={{A8C3B004-9B21-4BE2-B54A-97E0C28C2AA1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\MANIFeST OU
DefaultGroupName=MANIFeST OU
DisableProgramGroupPage=yes
OutputDir=..\..\build\installer
OutputBaseFilename=manifest_ou_1_2
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\..\app\static\img\manifest_ou.ico
UninstallDisplayIcon={app}\app\static\img\manifest_ou.ico

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Files]
Source: "{#StageDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Dirs]
Name: "{commonappdata}\ManifestFallschirm"; Permissions: users-modify
Name: "{commonappdata}\ManifestFallschirm\secrets"; Permissions: users-modify
Name: "{commonappdata}\ManifestFallschirm\logs"; Permissions: users-modify
Name: "{commonappdata}\ManifestFallschirm\data"; Permissions: users-modify
Name: "{commonappdata}\ManifestFallschirm\uploads"; Permissions: users-modify
Name: "{commonappdata}\ManifestFallschirm\session_data"; Permissions: users-modify

[Tasks]
Name: "desktopicon"; Description: "Desktop-Symbol erstellen"; GroupDescription: "Zusaetzliche Symbole:"; Flags: unchecked
Name: "taskbarpin"; Description: "An Taskleiste anheften (wenn unterstuetzt)"; GroupDescription: "Zusaetzliche Symbole:"; Flags: unchecked

[Icons]
Name: "{group}\MANIFeST OU"; Filename: "{app}\start_manifest_prod.vbs"; IconFilename: "{app}\app\static\img\manifest_ou.ico"
Name: "{autodesktop}\MANIFeST OU"; Filename: "{app}\start_manifest_prod.vbs"; IconFilename: "{app}\app\static\img\manifest_ou.ico"; Tasks: desktopicon

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\tools\pin_taskbar.ps1"" -TargetPath ""{app}\start_manifest_prod.vbs"""; StatusMsg: "Optionales Taskleisten-Pinning wird ausgefuehrt..."; Flags: runhidden waituntilterminated skipifsilent runasoriginaluser; Tasks: taskbarpin
; shellexec (statt direktem wscript.exe-Aufruf als Kindprozess von Setup.exe)
; ist zwingend noetig: ohne shellexec haengt der gestartete Prozessbaum
; (wscript.exe -> pythonw.exe -> Waitress) als Kindprozess am Job-Object von
; Setup.exe und wird von Windows beim Beenden von Setup.exe (Klick auf
; "Fertigstellen") sofort mitbeendet - "nowait" verhindert das NICHT, es
; sorgt nur dafuer, dass Setup nicht auf das Prozessende wartet. Per
; shellexec uebernimmt stattdessen der Windows-Shell-Broker den Start,
; genau wie beim manuellen Doppelklick auf die Desktop-Verknuepfung, und der
; Prozess bleibt nach Setup-Ende am Leben.
Filename: "{app}\start_manifest_prod.vbs"; Description: "MANIFeST OU starten"; Flags: postinstall shellexec nowait skipifsilent

[UninstallRun]
; Laeuft VOR dem Entfernen der Dateien: bittet einen eventuell noch
; laufenden Produktivserver um sauberes Beenden und wartet kurz, bis der
; Port frei ist. Verhindert, dass geladene DLLs/PYDs der Runtime (python.exe,
; python314.dll, native Erweiterungsmodule) die Deinstallation blockieren und
; Hunderte Dateien zurueckbleiben.
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$ErrorActionPreference = 'SilentlyContinue'; try {{ Invoke-WebRequest -Uri 'http://127.0.0.1:5000/pwa/runtime/shutdown' -Method POST -TimeoutSec 2 -UseBasicParsing | Out-Null }} catch {{}}; for ($i = 0; $i -lt 20; $i++) {{ $portOpen = $false; try {{ $c = New-Object System.Net.Sockets.TcpClient; $c.Connect('127.0.0.1', 5000); $portOpen = $true; $c.Close() }} catch {{}}; if (-not $portOpen) {{ break }}; Start-Sleep -Milliseconds 250 }}"""; Flags: runhidden waituntilterminated

[Code]
var
  LicensePage: TInputQueryWizardPage;
  PasswordPage: TInputQueryWizardPage;

function SetEnvironmentVariable(lpName, lpValue: String): Boolean;
  external 'SetEnvironmentVariableW@kernel32.dll stdcall';

function IsSilentInstall: Boolean;
begin
  Result := WizardSilent();
end;

function ParamValue(const ParamName: String): String;
begin
  Result := Trim(ExpandConstant('{param:' + ParamName + '|}'));
end;

function EffectiveLicenseKey: String;
begin
  Result := ParamValue('LICENSEKEY');
  if Result = '' then
    Result := Trim(LicensePage.Values[0]);
end;

function EffectiveAdminPassword: String;
begin
  Result := ParamValue('ADMINPASSWORD');
  if Result = '' then
    Result := PasswordPage.Values[0];
end;

function EffectiveAdminPasswordConfirm: String;
begin
  Result := ParamValue('ADMINPASSWORD');
  if Result = '' then
    Result := PasswordPage.Values[1];
end;

function EffectiveDbAdminPassword: String;
begin
  Result := ParamValue('DBADMINPASSWORD');
  if Result = '' then
    Result := PasswordPage.Values[2];
end;

function EffectiveDbAdminPasswordConfirm: String;
begin
  Result := ParamValue('DBADMINPASSWORD');
  if Result = '' then
    Result := PasswordPage.Values[3];
end;

function ProgramDataRoot: String;
begin
  Result := ExpandConstant('{commonappdata}\ManifestFallschirm');
end;

function ProgramDataSecretsPath(Param: String): String;
begin
  Result := ProgramDataRoot() + '\secrets\auth_config.json';
end;

procedure InitializeWizard;
var
  HintHeaderLabel, HintBodyLabel: TNewStaticText;
  RowHeight, RowTop, I: Integer;
  HintTop: Integer;
begin
  LicensePage := CreateInputQueryPage(
    wpSelectDir,
    'Lizenzschluessel',
    'Bitte Lizenzschluessel eingeben',
    'Der Schluessel wird lokal gespeichert und bei jedem Start geprueft.'
  );
  LicensePage.Add('Lizenzschluessel:', False);

  PasswordPage := CreateInputQueryPage(
    LicensePage.ID,
    'Admin-Konfiguration',
    'Admin- und DB-Admin-Passwort setzen',
    'Jedes Passwort bitte zur Kontrolle zweimal eingeben.'
  );
  PasswordPage.Add('Admin-Passwort:', False);
  PasswordPage.Add('Admin-Passwort wiederholen:', False);
  PasswordPage.Add('DB-Admin-Passwort:', False);
  PasswordPage.Add('DB-Admin-Passwort wiederholen:', False);

  { Die vier Felder enger packen als Innos Standardabstand, damit
    darunter garantiert genug Platz fuer den vollstaendig sichtbaren
    Warnhinweis bleibt (statt ihn abzuschneiden). Alle Masse nutzen
    ScaleX/ScaleY, damit das bei abweichender Windows-Skalierung stabil bleibt. }
  RowHeight := ScaleY(38);
  for I := 0 to 3 do
  begin
    RowTop := I * RowHeight;
    PasswordPage.PromptLabels[I].Top := RowTop;
    PasswordPage.Edits[I].Top := RowTop + PasswordPage.PromptLabels[I].Height + ScaleY(2);
  end;

  HintTop := 4 * RowHeight + ScaleY(14);

  HintHeaderLabel := TNewStaticText.Create(PasswordPage);
  HintHeaderLabel.Parent := PasswordPage.Surface;
  HintHeaderLabel.Left := 0;
  HintHeaderLabel.Top := HintTop;
  HintHeaderLabel.Width := PasswordPage.Surface.Width;
  HintHeaderLabel.AutoSize := True;
  HintHeaderLabel.Font.Style := [fsBold];
  HintHeaderLabel.Font.Size := HintHeaderLabel.Font.Size + 1;
  HintHeaderLabel.Caption := 'Wichtig:';

  HintBodyLabel := TNewStaticText.Create(PasswordPage);
  HintBodyLabel.Parent := PasswordPage.Surface;
  HintBodyLabel.Left := 0;
  HintBodyLabel.Top := HintHeaderLabel.Top + HintHeaderLabel.Height + ScaleY(4);
  HintBodyLabel.Width := PasswordPage.Surface.Width;
  { Hoehe fuellt den verbleibenden, tatsaechlich sichtbaren Platz der Seite
    (statt einer festen Pixelzahl), damit auf keiner Aufloesung/DPI-Stufe
    Text unten abgeschnitten wird. }
  HintBodyLabel.Height := PasswordPage.Surface.Height - HintBodyLabel.Top;
  HintBodyLabel.AutoSize := False;
  HintBodyLabel.WordWrap := True;
  HintBodyLabel.Font.Size := HintBodyLabel.Font.Size + 1;
  HintBodyLabel.Caption :=
    'Bitte beide Passwoerter sicher aufbewahren – sie werden spaeter fuer ' +
    'administrative Funktionen von MANIFeST OU benoetigt. Passwoerter werden ' +
    'nur als Hash gespeichert und koennen nicht angezeigt werden. Bei Verlust ' +
    'ist eine erneute Runtime-Konfiguration erforderlich.';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  L, A, AC, D, DC: String;
begin
  Result := True;

  if CurPageID = LicensePage.ID then
  begin
    L := EffectiveLicenseKey();
    if L = '' then
    begin
      MsgBox('Bitte Lizenzschluessel eingeben.', mbError, MB_OK);
      Result := False;
      exit;
    end;
  end;

  if CurPageID = PasswordPage.ID then
  begin
    A := EffectiveAdminPassword();
    AC := EffectiveAdminPasswordConfirm();
    D := EffectiveDbAdminPassword();
    DC := EffectiveDbAdminPasswordConfirm();

    if Length(A) = 0 then
    begin
      MsgBox('Admin-Passwort darf nicht leer sein.', mbError, MB_OK);
      Result := False;
      exit;
    end;

    if Length(AC) = 0 then
    begin
      MsgBox('Bitte das Admin-Passwort zur Kontrolle erneut eingeben.', mbError, MB_OK);
      Result := False;
      exit;
    end;

    if A <> AC then
    begin
      MsgBox(
        'Die beiden Eingaben fuer das Admin-Passwort stimmen nicht ueberein.' + #13#10 +
        'Bitte geben Sie das Passwort erneut ein.',
        mbError, MB_OK
      );
      Result := False;
      exit;
    end;

    if Length(D) = 0 then
    begin
      MsgBox('DB-Admin-Passwort darf nicht leer sein.', mbError, MB_OK);
      Result := False;
      exit;
    end;

    if Length(DC) = 0 then
    begin
      MsgBox('Bitte das DB-Admin-Passwort zur Kontrolle erneut eingeben.', mbError, MB_OK);
      Result := False;
      exit;
    end;

    if D <> DC then
    begin
      MsgBox(
        'Die beiden Eingaben fuer das DB-Admin-Passwort stimmen nicht ueberein.' + #13#10 +
        'Bitte geben Sie das Passwort erneut ein.',
        mbError, MB_OK
      );
      Result := False;
      exit;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  L, A, AC, D, DC: String;
begin
  Result := '';
  L := EffectiveLicenseKey();
  A := EffectiveAdminPassword();
  AC := EffectiveAdminPasswordConfirm();
  D := EffectiveDbAdminPassword();
  DC := EffectiveDbAdminPasswordConfirm();

  if L = '' then
  begin
    Result := 'Lizenzschluessel fehlt.';
    exit;
  end;

  if Length(A) = 0 then
  begin
    Result := 'Admin-Passwort darf nicht leer sein.';
    exit;
  end;

  if A <> AC then
  begin
    Result := 'Die beiden Eingaben fuer das Admin-Passwort stimmen nicht ueberein.';
    exit;
  end;

  if Length(D) = 0 then
  begin
    Result := 'DB-Admin-Passwort darf nicht leer sein.';
    exit;
  end;

  if D <> DC then
  begin
    Result := 'Die beiden Eingaben fuer das DB-Admin-Passwort stimmen nicht ueberein.';
    exit;
  end;
end;

procedure ClearInstallSecretsEnv;
begin
  SetEnvironmentVariable('MANIFEST_INSTALL_LICENSE_KEY', '');
  SetEnvironmentVariable('MANIFEST_INSTALL_ADMIN_PASSWORD', '');
  SetEnvironmentVariable('MANIFEST_INSTALL_ADMIN_PASSWORD_CONFIRM', '');
  SetEnvironmentVariable('MANIFEST_INSTALL_DB_ADMIN_PASSWORD', '');
  SetEnvironmentVariable('MANIFEST_INSTALL_DB_ADMIN_PASSWORD_CONFIRM', '');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  pythonExe, scriptPath, secretsPath, paramsLine: String;
  execOk: Boolean;
begin
  if CurStep <> ssPostInstall then
    exit;

  pythonExe := ExpandConstant('{app}\runtime\python\python.exe');
  scriptPath := ExpandConstant('{app}\tools\license\install_runtime_secrets.py');
  secretsPath := ProgramDataSecretsPath('');

  { Secrets travel via environment variables, not command-line arguments,
    so they are not visible in process listings of other local admins. }
  SetEnvironmentVariable('MANIFEST_INSTALL_LICENSE_KEY', EffectiveLicenseKey());
  SetEnvironmentVariable('MANIFEST_INSTALL_ADMIN_PASSWORD', EffectiveAdminPassword());
  SetEnvironmentVariable('MANIFEST_INSTALL_ADMIN_PASSWORD_CONFIRM', EffectiveAdminPasswordConfirm());
  SetEnvironmentVariable('MANIFEST_INSTALL_DB_ADMIN_PASSWORD', EffectiveDbAdminPassword());
  SetEnvironmentVariable('MANIFEST_INSTALL_DB_ADMIN_PASSWORD_CONFIRM', EffectiveDbAdminPasswordConfirm());

  paramsLine := '"' + scriptPath + '" --secrets-path "' + secretsPath + '"';

  execOk := Exec(pythonExe, paramsLine, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
  ClearInstallSecretsEnv;

  if not execOk then
  begin
    MsgBox(
      'Die Runtime-Konfiguration (Lizenz- und Passwort-Einrichtung) konnte nicht gestartet werden.' + #13#10 +
      'Die Installation wird abgebrochen.',
      mbCriticalError, MB_OK
    );
    Abort;
  end;

  if ResultCode <> 0 then
  begin
    MsgBox(
      'Die Runtime-Konfiguration (Lizenz- und Passwort-Einrichtung) ist fehlgeschlagen (Code ' + IntToStr(ResultCode) + ').' + #13#10 +
      'Bitte Lizenzschluessel und Passwoerter pruefen und die Installation erneut starten.' + #13#10 +
      'Die Installation wird abgebrochen.',
      mbCriticalError, MB_OK
    );
    Abort;
  end;

  if not FileExists(secretsPath) then
  begin
    MsgBox(
      'Die Secrets-Datei wurde nicht erzeugt: ' + secretsPath + #13#10 +
      'Die Installation wird abgebrochen.',
      mbCriticalError, MB_OK
    );
    Abort;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  dataRoot: String;
  shouldDelete: Boolean;
begin
  if CurUninstallStep <> usUninstall then
    exit;

  dataRoot := ProgramDataRoot();
  if not DirExists(dataRoot) then
    exit;

  shouldDelete := False;
  if ParamValue('CLEANPROGRAMDATA') = '1' then
  begin
    shouldDelete := True;
  end
  else if UninstallSilent then
  begin
    shouldDelete := False;
  end
  else
  begin
    if MsgBox(
      'Sollen ProgramData-Dateien geloescht werden?' + #13#10 +
      dataRoot + #13#10 +
      '(Nein = Lizenz/Backups/Config behalten)',
      mbConfirmation,
      MB_YESNO
    ) = IDYES then
    begin
      shouldDelete := True;
    end;
  end;

  if shouldDelete then
  begin
    DelTree(dataRoot, True, True, True);
  end;
end;
