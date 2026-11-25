; AreaGrab 1.1 — per-user install, no UAC.
; Build first:  pyinstaller --noconfirm --clean AreaGrab.spec
; Then compile: iscc areagrab_setup.iss

#define MyAppVersion "1.1.0"

[Setup]
AppId={{A7D4C2E1-5B3F-4E8A-9C21-6F0D8B7A1E42}
AppName=AreaGrab
AppVersion={#MyAppVersion}
AppVerName=AreaGrab {#MyAppVersion}
AppPublisher=AreaGrab
AppPublisherURL=https://areagrab.com/
AppSupportURL=https://areagrab.com/
AppUpdatesURL=https://areagrab.com/
DefaultDirName={localappdata}\Programs\AreaGrab
DefaultGroupName=AreaGrab
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=AreaGrab_Setup_{#MyAppVersion}
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
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"; LicenseFile: "installer\legal\ru\license.txt"; InfoBeforeFile: "installer\legal\ru\privacy.txt"
Name: "chinesesimplified"; MessagesFile: "installer\languages\ChineseSimplified.isl"; LicenseFile: "installer\legal\zh-CN\license.txt"; InfoBeforeFile: "installer\legal\zh-CN\privacy.txt"
Name: "chinesetraditional"; MessagesFile: "installer\languages\ChineseTraditional.isl"; LicenseFile: "installer\legal\zh-TW\license.txt"; InfoBeforeFile: "installer\legal\zh-TW\privacy.txt"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"; LicenseFile: "installer\legal\de\license.txt"; InfoBeforeFile: "installer\legal\de\privacy.txt"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"; LicenseFile: "installer\legal\fr\license.txt"; InfoBeforeFile: "installer\legal\fr\privacy.txt"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"; LicenseFile: "installer\legal\es\license.txt"; InfoBeforeFile: "installer\legal\es\privacy.txt"
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"; LicenseFile: "installer\legal\pt-BR\license.txt"; InfoBeforeFile: "installer\legal\pt-BR\privacy.txt"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"; LicenseFile: "installer\legal\it\license.txt"; InfoBeforeFile: "installer\legal\it\privacy.txt"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"; LicenseFile: "installer\legal\pl\license.txt"; InfoBeforeFile: "installer\legal\pl\privacy.txt"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"; LicenseFile: "installer\legal\ja\license.txt"; InfoBeforeFile: "installer\legal\ja\privacy.txt"
Name: "korean"; MessagesFile: "compiler:Languages\Korean.isl"; LicenseFile: "installer\legal\ko\license.txt"; InfoBeforeFile: "installer\legal\ko\privacy.txt"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"; LicenseFile: "installer\legal\tr\license.txt"; InfoBeforeFile: "installer\legal\tr\privacy.txt"

[CustomMessages]
english.AdditionalOptions=Additional options:
english.StartWithWindows=Start AreaGrab when signing in to Windows
english.UpgradeDetected=An existing installation or a running instance of AreaGrab was found.
english.InstalledVersion=Installed version: %1
english.IncomingVersion=Version to install: %1
english.ConfirmUpgrade=Install this build over the existing one? Settings and saved screenshots will be kept.
english.CloseWarning=AreaGrab will close after confirmation. Unsaved screenshots in memory will be lost.
english.CloseFailed=AreaGrab did not close automatically. Exit from its tray menu before updating.
english.RetryClose=Exit AreaGrab from its tray menu and select Retry.
english.UpgradeCancelled=Update cancelled because AreaGrab is still running.

russian.AdditionalOptions=Дополнительные параметры:
russian.StartWithWindows=Запускать AreaGrab при входе в Windows
russian.UpgradeDetected=Обнаружена предыдущая установка или запущенный AreaGrab.
russian.InstalledVersion=Установленная версия: %1
russian.IncomingVersion=Устанавливаемая версия: %1
russian.ConfirmUpgrade=Установить эту сборку поверх существующей? Настройки и сохранённые снимки останутся на месте.
russian.CloseWarning=После подтверждения AreaGrab закроется. Несохранённые снимки в памяти будут потеряны.
russian.CloseFailed=AreaGrab не завершился автоматически. Перед обновлением закройте его через меню значка в трее.
russian.RetryClose=Закройте AreaGrab через меню значка в трее и нажмите «Повторить».
russian.UpgradeCancelled=Обновление отменено, так как AreaGrab ещё запущен.

chinesesimplified.AdditionalOptions=其他选项：
chinesesimplified.StartWithWindows=登录 Windows 时启动 AreaGrab
chinesesimplified.UpgradeDetected=检测到已安装或正在运行的 AreaGrab。
chinesesimplified.InstalledVersion=已安装版本：%1
chinesesimplified.IncomingVersion=将安装的版本：%1
chinesesimplified.ConfirmUpgrade=要覆盖安装此版本吗？设置和已保存的截图将保留。
chinesesimplified.CloseWarning=确认后 AreaGrab 将关闭。内存中未保存的截图将丢失。
chinesesimplified.CloseFailed=AreaGrab 未自动关闭。更新前请从托盘菜单退出。
chinesesimplified.RetryClose=请从托盘菜单退出 AreaGrab，然后选择“重试”。
chinesesimplified.UpgradeCancelled=AreaGrab 仍在运行，更新已取消。

chinesetraditional.AdditionalOptions=其他選項：
chinesetraditional.StartWithWindows=登入 Windows 時啟動 AreaGrab
chinesetraditional.UpgradeDetected=偵測到已安裝或正在執行的 AreaGrab。
chinesetraditional.InstalledVersion=已安裝版本：%1
chinesetraditional.IncomingVersion=即將安裝的版本：%1
chinesetraditional.ConfirmUpgrade=要覆蓋安裝此版本嗎？設定與已儲存的截圖將保留。
chinesetraditional.CloseWarning=確認後 AreaGrab 將關閉。記憶體中未儲存的截圖將遺失。
chinesetraditional.CloseFailed=AreaGrab 未自動關閉。更新前請從系統匣選單結束程式。
chinesetraditional.RetryClose=請從系統匣選單結束 AreaGrab，然後選擇「重試」。
chinesetraditional.UpgradeCancelled=AreaGrab 仍在執行，更新已取消。

spanish.AdditionalOptions=Opciones adicionales:
spanish.StartWithWindows=Iniciar AreaGrab al entrar en Windows
spanish.UpgradeDetected=Se detectó una instalación anterior o una instancia de AreaGrab en ejecución.
spanish.InstalledVersion=Versión instalada: %1
spanish.IncomingVersion=Versión que se instalará: %1
spanish.ConfirmUpgrade=¿Instalar esta compilación sobre la existente? Se conservarán la configuración y las capturas guardadas.
spanish.CloseWarning=AreaGrab se cerrará al confirmar. Se perderán las capturas sin guardar en memoria.
spanish.CloseFailed=AreaGrab no se cerró automáticamente. Sal desde su menú de la bandeja antes de actualizar.
spanish.RetryClose=Sal de AreaGrab desde la bandeja y selecciona Reintentar.
spanish.UpgradeCancelled=Actualización cancelada porque AreaGrab sigue en ejecución.

brazilianportuguese.AdditionalOptions=Opções adicionais:
brazilianportuguese.StartWithWindows=Iniciar o AreaGrab ao entrar no Windows
brazilianportuguese.UpgradeDetected=Foi detectada uma instalação anterior ou uma instância do AreaGrab em execução.
brazilianportuguese.InstalledVersion=Versão instalada: %1
brazilianportuguese.IncomingVersion=Versão a instalar: %1
brazilianportuguese.ConfirmUpgrade=Instalar esta versão sobre a existente? As configurações e capturas salvas serão mantidas.
brazilianportuguese.CloseWarning=O AreaGrab será fechado após a confirmação. Capturas não salvas na memória serão perdidas.
brazilianportuguese.CloseFailed=O AreaGrab não fechou automaticamente. Saia pelo menu da bandeja antes de atualizar.
brazilianportuguese.RetryClose=Saia do AreaGrab pelo menu da bandeja e selecione Repetir.
brazilianportuguese.UpgradeCancelled=Atualização cancelada porque o AreaGrab ainda está em execução.

german.AdditionalOptions=Weitere Optionen:
german.StartWithWindows=AreaGrab bei der Windows-Anmeldung starten
german.UpgradeDetected=Eine vorhandene Installation oder laufende Instanz von AreaGrab wurde gefunden.
german.InstalledVersion=Installierte Version: %1
german.IncomingVersion=Zu installierende Version: %1
german.ConfirmUpgrade=Diesen Build über die vorhandene Version installieren? Einstellungen und gespeicherte Screenshots bleiben erhalten.
german.CloseWarning=AreaGrab wird nach der Bestätigung geschlossen. Ungespeicherte Screenshots im Arbeitsspeicher gehen verloren.
german.CloseFailed=AreaGrab wurde nicht automatisch beendet. Beenden Sie es vor der Aktualisierung über das Infobereichsmenü.
german.RetryClose=Beenden Sie AreaGrab über das Infobereichsmenü und wählen Sie Wiederholen.
german.UpgradeCancelled=Aktualisierung abgebrochen, da AreaGrab noch läuft.

french.AdditionalOptions=Options supplémentaires :
french.StartWithWindows=Lancer AreaGrab à l’ouverture de session Windows
french.UpgradeDetected=Une installation existante ou une instance d’AreaGrab en cours d’exécution a été détectée.
french.InstalledVersion=Version installée : %1
french.IncomingVersion=Version à installer : %1
french.ConfirmUpgrade=Installer cette version par-dessus l’existante ? Les paramètres et captures enregistrées seront conservés.
french.CloseWarning=AreaGrab se fermera après confirmation. Les captures non enregistrées en mémoire seront perdues.
french.CloseFailed=AreaGrab ne s’est pas fermé automatiquement. Quittez-le depuis le menu de la zone de notification avant la mise à jour.
french.RetryClose=Quittez AreaGrab depuis la zone de notification, puis sélectionnez Réessayer.
french.UpgradeCancelled=Mise à jour annulée car AreaGrab est toujours en cours d’exécution.

japanese.AdditionalOptions=追加のオプション:
japanese.StartWithWindows=Windows にサインインしたときに AreaGrab を起動
japanese.UpgradeDetected=既存のインストールまたは実行中の AreaGrab が見つかりました。
japanese.InstalledVersion=インストール済みのバージョン: %1
japanese.IncomingVersion=インストールするバージョン: %1
japanese.ConfirmUpgrade=既存のバージョンに上書きインストールしますか？設定と保存済みの画像は保持されます。
japanese.CloseWarning=確認後に AreaGrab を終了します。メモリ内の未保存画像は失われます。
japanese.CloseFailed=AreaGrab が自動終了しませんでした。更新前にトレイメニューから終了してください。
japanese.RetryClose=トレイメニューから AreaGrab を終了し、［再試行］を選んでください。
japanese.UpgradeCancelled=AreaGrab が実行中のため、更新をキャンセルしました。

korean.AdditionalOptions=추가 옵션:
korean.StartWithWindows=Windows 로그인 시 AreaGrab 시작
korean.UpgradeDetected=기존 설치 또는 실행 중인 AreaGrab이 감지되었습니다.
korean.InstalledVersion=설치된 버전: %1
korean.IncomingVersion=설치할 버전: %1
korean.ConfirmUpgrade=기존 버전에 덮어쓸까요? 설정과 저장된 스크린샷은 유지됩니다.
korean.CloseWarning=확인하면 AreaGrab이 종료됩니다. 메모리에 있는 저장하지 않은 스크린샷은 사라집니다.
korean.CloseFailed=AreaGrab이 자동으로 종료되지 않았습니다. 업데이트 전에 트레이 메뉴에서 종료하세요.
korean.RetryClose=트레이 메뉴에서 AreaGrab을 종료하고 다시 시도를 선택하세요.
korean.UpgradeCancelled=AreaGrab이 아직 실행 중이어서 업데이트가 취소되었습니다.

turkish.AdditionalOptions=Ek seçenekler:
turkish.StartWithWindows=Windows oturumu açıldığında AreaGrab’ı başlat
turkish.UpgradeDetected=Önceki bir kurulum veya çalışan bir AreaGrab örneği bulundu.
turkish.InstalledVersion=Yüklü sürüm: %1
turkish.IncomingVersion=Yüklenecek sürüm: %1
turkish.ConfirmUpgrade=Bu derleme mevcut sürümün üzerine yüklensin mi? Ayarlar ve kaydedilmiş görüntüler korunur.
turkish.CloseWarning=Onaylandığında AreaGrab kapanır. Bellekteki kaydedilmemiş görüntüler silinir.
turkish.CloseFailed=AreaGrab otomatik kapanmadı. Güncellemeden önce sistem tepsisi menüsünden çıkın.
turkish.RetryClose=Sistem tepsisi menüsünden AreaGrab’dan çıkın ve Yeniden Dene’yi seçin.
turkish.UpgradeCancelled=AreaGrab hâlâ çalıştığı için güncelleme iptal edildi.

italian.AdditionalOptions=Opzioni aggiuntive:
italian.StartWithWindows=Avvia AreaGrab all’accesso a Windows
italian.UpgradeDetected=È stata rilevata un’installazione precedente o un’istanza di AreaGrab in esecuzione.
italian.InstalledVersion=Versione installata: %1
italian.IncomingVersion=Versione da installare: %1
italian.ConfirmUpgrade=Installare questa build sopra quella esistente? Le impostazioni e le schermate salvate verranno conservate.
italian.CloseWarning=AreaGrab verrà chiuso dopo la conferma. Le schermate non salvate in memoria andranno perse.
italian.CloseFailed=AreaGrab non si è chiuso automaticamente. Esci dal menu nell’area di notifica prima di aggiornare.
italian.RetryClose=Chiudi AreaGrab dal menu nell’area di notifica e seleziona Riprova.
italian.UpgradeCancelled=Aggiornamento annullato perché AreaGrab è ancora in esecuzione.

polish.AdditionalOptions=Dodatkowe opcje:
polish.StartWithWindows=Uruchamiaj AreaGrab przy logowaniu do Windows
polish.UpgradeDetected=Wykryto istniejącą instalację lub uruchomiony program AreaGrab.
polish.InstalledVersion=Zainstalowana wersja: %1
polish.IncomingVersion=Wersja do zainstalowania: %1
polish.ConfirmUpgrade=Zainstalować tę kompilację na istniejącej wersji? Ustawienia i zapisane zrzuty zostaną zachowane.
polish.CloseWarning=Po potwierdzeniu AreaGrab zostanie zamknięty. Niezapisane zrzuty w pamięci przepadną.
polish.CloseFailed=AreaGrab nie zamknął się automatycznie. Przed aktualizacją zamknij go z menu zasobnika.
polish.RetryClose=Zamknij AreaGrab z menu zasobnika i wybierz Ponów próbę.
polish.UpgradeCancelled=Aktualizację anulowano, ponieważ AreaGrab nadal działa.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "{cm:StartWithWindows}"; GroupDescription: "{cm:AdditionalOptions}"; Check: IsFreshProfile

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
Root: HKCU; Subkey: "Software\AreaGrab"; ValueType: string; ValueName: "InitialLanguage"; ValueData: "{code:InitialLanguage}"; Flags: createvalueifdoesntexist uninsdeletevalue; Check: IsFreshProfile
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "AreaGrab"; ValueData: """{app}\AreaGrab.exe"" --autostart"; Flags: uninsdeletevalue; Tasks: autostart; Check: IsFreshProfile

[Run]
Filename: "{app}\AreaGrab.exe"; Description: "{cm:LaunchProgram,AreaGrab}"; Flags: nowait postinstall skipifsilent


[Code]
function IsFreshProfile(): Boolean;
begin
  Result := not FileExists(ExpandConstant('{userappdata}\AreaGrab\settings.json'));
end;

function InitialLanguage(Param: String): String;
var
  Lang: String;
begin
  Lang := ActiveLanguage;
  Result := 'en';
  if Lang = 'russian' then Result := 'ru'
  else if Lang = 'chinesesimplified' then Result := 'zh-CN'
  else if Lang = 'chinesetraditional' then Result := 'zh-TW'
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
  AreaGrabUninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{A7D4C2E1-5B3F-4E8A-9C21-6F0D8B7A1E42}_is1';

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

  Prompt := CustomMessage('UpgradeDetected') + #13#10 + #13#10;
  if ExistingVersion <> '' then
    Prompt := Prompt + FmtMessage(CustomMessage('InstalledVersion'), [ExistingVersion]) + #13#10;
  Prompt := Prompt + FmtMessage(CustomMessage('IncomingVersion'), ['{#MyAppVersion}']) + #13#10 + #13#10 +
    CustomMessage('ConfirmUpgrade');
  if Running then
    Prompt := Prompt + #13#10 + #13#10 + CustomMessage('CloseWarning');

  { Silent upgrades must explicitly opt in. }
  if WizardSilent then
  begin
    Result := ExpandConstant('{param:AREAGRABUPDATE|0}') = '1';
    Exit;
  end;
  Result := TaskDialogMsgBox('', Prompt, mbConfirmation, MB_YESNO, [
    SetupMessage(msgButtonYes), SetupMessage(msgButtonNo)], 0) = IDYES;
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
    Result := CustomMessage('CloseFailed');
    Exit;
  end;
  while CheckForMutexes('AreaGrab_SingleInstance_v1') do
  begin
    if TaskDialogMsgBox('', CustomMessage('RetryClose'), mbConfirmation, MB_RETRYCANCEL, [
      SetupMessage(msgRetryCancelRetry), SetupMessage(msgButtonCancel)], 0) <> IDRETRY then
    begin
      Result := CustomMessage('UpgradeCancelled');
      Exit;
    end;
  end;
end;
