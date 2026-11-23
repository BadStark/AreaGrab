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
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AreaGrab"; ValueData: """{app}\AreaGrab.exe"" --autostart"; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\AreaGrab.exe"; Description: "{cm:LaunchProgram,AreaGrab}"; Flags: nowait postinstall skipifsilent


[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  { Never replace files while the screenshot hook or tray is still running.
    Avoid force-killing the process: users may have RAM-only screenshots. }
  while CheckForMutexes('AreaGrab_SingleInstance_v1') do
  begin
    if WizardSilent then
    begin
      Result := 'AreaGrab запущен. Закройте приложение через меню в трее перед обновлением.';
      Exit;
    end;
    if MsgBox(
      'AreaGrab сейчас запущен.' + #13#10 + #13#10 +
      'Нажмите правой кнопкой мыши на значок AreaGrab возле часов и выберите «Выход».' +
      #13#10 + 'Затем нажмите «Повторить», чтобы продолжить обновление.' + #13#10 + #13#10 +
      'Настройки и сохранённые скриншоты останутся на месте.',
      mbConfirmation, MB_RETRYCANCEL
    ) <> IDRETRY then
    begin
      Result := 'Установка отменена: сначала необходимо закрыть AreaGrab.';
      Exit;
    end;
  end;
end;
