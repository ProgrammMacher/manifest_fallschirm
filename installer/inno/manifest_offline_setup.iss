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
Name: "{commonappdata}\ManifestFallschirm\venv"; Permissions: users-modify

[Tasks]
Name: "desktopicon"; Description: "Desktop-Symbol erstellen"; GroupDescription: "Zusaetzliche Symbole:"; Flags: unchecked
Name: "taskbarpin"; Description: "An Taskleiste anheften (wenn unterstuetzt)"; GroupDescription: "Zusaetzliche Symbole:"; Flags: unchecked

[Icons]
Name: "{group}\MANIFeST OU"; Filename: "{app}\start_manifest_prod.vbs"; IconFilename: "{app}\app\static\img\manifest_ou.ico"
Name: "{autodesktop}\MANIFeST OU"; Filename: "{app}\start_manifest_prod.vbs"; IconFilename: "{app}\app\static\img\manifest_ou.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\runtime\python\python.exe"; Parameters: """{app}\tools\license\install_runtime_secrets.py"" --secrets-path ""{code:ProgramDataSecretsPath}"" --license-key ""{code:GetLicenseKey}"" --admin-password ""{code:GetAdminPassword}"" --db-admin-password ""{code:GetDbAdminPassword}"""; WorkingDir: "{app}"; StatusMsg: "Konfiguriere Lizenz und Admin-Passwoerter..."; Flags: runhidden waituntilterminated
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\tools\pin_taskbar.ps1"" -TargetPath ""{app}\start_manifest_prod.vbs"""; StatusMsg: "Optionales Taskleisten-Pinning wird ausgefuehrt..."; Flags: runhidden waituntilterminated skipifsilent; Tasks: taskbarpin
Filename: "{sys}\wscript.exe"; Parameters: """{app}\start_manifest_prod.vbs"""; Description: "MANIFeST OU starten"; Flags: postinstall nowait skipifsilent

[Code]
var
  LicensePage: TInputQueryWizardPage;
  PasswordPage: TInputQueryWizardPage;

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

function EffectiveDbAdminPassword: String;
begin
  Result := ParamValue('DBADMINPASSWORD');
  if Result = '' then
    Result := PasswordPage.Values[1];
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
    'Passwoerter sind sichtbar, damit Tippfehler erkennbar sind.'
  );
  PasswordPage.Add('Admin-Passwort:', False);
  PasswordPage.Add('DB-Admin-Passwort:', False);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  L, A, D: String;
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
    D := EffectiveDbAdminPassword();

    if Length(Trim(A)) = 0 then
    begin
      MsgBox('Admin-Passwort darf nicht leer sein.', mbError, MB_OK);
      Result := False;
      exit;
    end;

    if Length(Trim(D)) = 0 then
    begin
      MsgBox('DB-Admin-Passwort darf nicht leer sein.', mbError, MB_OK);
      Result := False;
      exit;
    end;
  end;
end;

function GetLicenseKey(Param: String): String;
begin
  Result := EffectiveLicenseKey();
end;

function GetAdminPassword(Param: String): String;
begin
  Result := EffectiveAdminPassword();
end;

function GetDbAdminPassword(Param: String): String;
begin
  Result := EffectiveDbAdminPassword();
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  L, A, D: String;
begin
  Result := '';
  L := EffectiveLicenseKey();
  A := EffectiveAdminPassword();
  D := EffectiveDbAdminPassword();

  if L = '' then
  begin
    Result := 'Lizenzschluessel fehlt.';
    exit;
  end;

  if Length(Trim(A)) = 0 then
  begin
    Result := 'Admin-Passwort darf nicht leer sein.';
    exit;
  end;

  if Length(Trim(D)) = 0 then
  begin
    Result := 'DB-Admin-Passwort darf nicht leer sein.';
    exit;
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
