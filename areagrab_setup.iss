; AreaGrab 1.1 — per-user install, no UAC.
; Build first:  pyinstaller --noconfirm --clean AreaGrab.spec
; Then compile: iscc areagrab_setup.iss

[Setup]
AppId={{A7D4C2E1-5B3F-4E8A-9C21-6F0D8B7A1E42}
AppName=AreaGrab
AppVersion=1.1.0
AppVerName=AreaGrab 1.1.0
AppPublisher=AreaGrab
AppPublisherURL=https://areagrab.com/
AppSupportURL=https://areagrab.com/
AppUpdatesURL=https://areagrab.com/
DefaultDirName={localappdata}\Programs\AreaGrab
DefaultGroupName=AreaGrab
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=AreaGrab_Setup_1.1.0
OutputDir=Output_v11
SetupIconFile=areagrab_v2.ico
UninstallDisplayIcon={app}\AreaGrab.exe
WizardStyle=modern
ShowLanguageDialog=yes
LanguageDetectionMethod=uilanguage
UsePreviousLanguage=yes
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
CloseApplications=yes
RestartApplications=no
; A running instance must be closed before overwriting its binaries.
; AppMutex matches areagrab/constants.py and is stable across upgrades.
AppMutex=AreaGrab_SingleInstance_v1
SetupLogging=yes
; --- Legal documents ---
LicenseFile=LicenseAgreement.rtf
InfoBeforeFile=PrivacyPolicy.rtf

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Запускать AreaGrab при входе в Windows"; GroupDescription: "Дополнительно:"

[Files]
Source: "dist_final\AreaGrab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LicenseAgreement.rtf"; DestDir: "{app}"; Flags: ignoreversion
Source: "PrivacyPolicy.rtf"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\AreaGrab"; Filename: "{app}\AreaGrab.exe"
Name: "{group}\{cm:UninstallProgram,AreaGrab}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\AreaGrab"; Filename: "{app}\AreaGrab.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\AreaGrab"; ValueType: string; ValueName: "InitialLanguage"; ValueData: "{code:InitialLanguage}"; Flags: createvalueifdoesntexist uninsdeletevalue
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AreaGrab"; ValueData: """{app}\AreaGrab.exe"" --autostart"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\AreaGrab.exe"; Description: "{cm:LaunchProgram,AreaGrab}"; Flags: nowait postinstall skipifsilent


[Code]
function InitialLanguage(Param: String): String;
var
  Lang: String;
begin
  Lang := ActiveLanguage;
  Result := 'en';
  if Lang = 'russian' then Result := 'ru'
  else if Lang = 'german' then Result := 'de'
  else if Lang = 'french' then Result := 'fr'
  else if Lang = 'spanish' then Result := 'es'
  else if Lang = 'brazilianportuguese' then Result := 'pt-BR'
  else if Lang = 'italian' then Result := 'it'
  else if Lang = 'polish' then Result := 'pl'
  else if Lang = 'japanese' then Result := 'ja'
  else if Lang = 'korean' then Result := 'ko'
  else if Lang = 'turkish' then Result := 'tr';
end;

function OpenEventW(DesiredAccess: Cardinal; InheritHandle: Boolean; Name: String): THandle;
  external 'OpenEventW@kernel32.dll stdcall';
function SetEvent(EventHandle: THandle): Boolean;
  external 'SetEvent@kernel32.dll stdcall';
function CloseHandle(Handle: THandle): Boolean;
  external 'CloseHandle@kernel32.dll stdcall';

function RequestAreaGrabExit(): Boolean;
var
  EventHandle: THandle;
begin
  EventHandle := OpenEventW($0002, False, 'Local\AreaGrab_InstallerShutdown_v1');
  Result := EventHandle <> 0;
  if Result then
  begin
    Result := SetEvent(EventHandle);
    CloseHandle(EventHandle);
  end;
end;

const
  AreaGrabUninstallKey = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\{A7D4C2E1-5B3F-4E8A-9C21-6F0D8B7A1E42}_is1';

function InitializeSetup(): Boolean;
var
  ExistingVersion: String;
  ExistingName: String;
  Running: Boolean;
  Prompt: String;
begin
  Result := True;
  ExistingVersion := '';
  ExistingName := '';
  { Inno Setup uses the stable AppId to register installed versions. }
  if not RegQueryStringValue(HKCU, AreaGrabUninstallKey, 'DisplayVersion', ExistingVersion) then
    RegQueryStringValue(HKCU, AreaGrabUninstallKey, 'DisplayName', ExistingName);
  Running := CheckForMutexes('AreaGrab_SingleInstance_v1');
  if (ExistingVersion = '') and (ExistingName = '') and not Running then
    Exit;

  Prompt := 'На компьютере обнаружена предыдущая установка или запущенный AreaGrab.' +
    ' ' + #13#10 + #13#10;
  if ExistingVersion <> '' then
    Prompt := Prompt + 'Установленная версия: ' + ExistingVersion + #13#10;
  Prompt := Prompt + 'Версия устанавливаемой сборки: 1.1.0' +
    ' ' + #13#10 + #13#10 +
    'Установить выбранную сборку поверх существующей?' + #13#10 +
    'Настройки и сохранённые снимки останутся на месте.';
  if Running then
    Prompt := Prompt + #13#10 + #13#10 +
      'AreaGrab будет закрыт автоматически после подтверждения.' + #13#10 +
      'Несохранённая история снимков в памяти будет потеряна.';

  { Silent installs must opt in to replacing an existing installation. }
  if WizardSilent then
  begin
    Result := False;
    Exit;
  end;
  Result := MsgBox(Prompt, mbConfirmation, MB_YESNO) = IDYES;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Attempts: Integer;
begin
  Result := '';
  if not CheckForMutexes('AreaGrab_SingleInstance_v1') then
    Exit;
  if RequestAreaGrabExit() then
  begin
    for Attempts := 1 to 100 do
    begin
      if not CheckForMutexes('AreaGrab_SingleInstance_v1') then
        Exit;
      Sleep(100);
    end;
  end;
  { Old versions do not listen for shutdown requests. Never force-kill. }
  if WizardSilent then
  begin
    Result := 'AreaGrab не завершился автоматически. Закройте его перед обновлением.';
    Exit;
  end;
  while CheckForMutexes('AreaGrab_SingleInstance_v1') do
  begin
    if MsgBox(
      'Не удалось автоматически закрыть AreaGrab.' + #13#10 +
      'Закройте программу через значок возле часов и нажмите «Повторить».',
      mbConfirmation, MB_RETRYCANCEL
    ) <> IDRETRY then
    begin
      Result := 'Обновление отменено: AreaGrab ещё запущен.';
      Exit;
    end;
  end;
end;
