; Diktiertool - Windows-Installer (Inno Setup).
;
; Erzeugt eine einzige DiktiertoolSetup.exe, die ein portables Python (ohne
; Systemeingriff), die Abhaengigkeiten und bei Bedarf die WebView2-Runtime
; einrichtet und eine Desktop-Verknuepfung anlegt. Windows-Pendant zu
; ../bootstrap.sh + ../../setup.sh.
;
; Bauen (auf Windows, oder z.B. via GitHub Actions windows-latest-Runner):
;   iscc installscript\windows\setup.iss
; Ergebnis liegt danach in installscript\windows\dist\DiktiertoolSetup.exe.
;
; Der Installer selbst enthaelt keinen Programmcode - er laedt ihn bei der
; Installation von GitHub (wie bootstrap.sh unter Linux), braucht also eine
; Internetverbindung. Das haelt den Installer klein und die Installation
; immer auf dem neuesten main-Stand.

#define MyAppName "Diktiertool"
; Von aussen ueberschreibbar: der Release-Workflow gibt die Version des
; gepushten v*-Tags mit "iscc /DMyAppVersion=1.0.1 ..." herein und prueft
; vorher, dass sie zu config.py passt.
#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "Diktiertool"
#define MyAppURL "https://github.com/CrazyJimPro/diktiertool"

[Setup]
AppId={{9A4C7E11-2D58-4F3A-B7E6-DIKTIERTOOL01}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\Diktiertool
DefaultGroupName=Diktiertool
DisableProgramGroupPage=yes
; Keine Adminrechte noetig - Installation landet unter %LOCALAPPDATA%, Python
; laeuft portabel, die WebView2-Runtime installiert sich notfalls als
; Benutzerinstallation.
PrivilegesRequired=lowest
; Ohne das laeuft Setup.exe als 32-Bit-Prozess unter WOW64, und ein Aufruf von
; "powershell.exe" ohne Pfad wuerde per Dateisystem-Umleitung auf der
; 32-Bit-PowerShell aus SysWOW64 landen. Das portable Python ist ein
; amd64-Build und braucht die echte 64-Bit-Umgebung.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=DiktiertoolSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={uninstallexe}

[Files]
Source: "find-python.ps1"; DestDir: "{app}\installscript\windows"; Flags: ignoreversion
Source: "bootstrap.ps1"; DestDir: "{app}\installscript\windows"; Flags: ignoreversion
Source: "install.ps1"; DestDir: "{app}\installscript\windows"; Flags: ignoreversion
Source: "start.ps1"; DestDir: "{app}\installscript\windows"; Flags: ignoreversion
Source: "uninstall.ps1"; DestDir: "{app}\installscript\windows"; Flags: ignoreversion

; Die eigentliche Verknuepfung legt install.ps1 auf dem Desktop an - sie zeigt
; direkt auf pythonw.exe im Installationsordner, dessen Pfad hier noch nicht
; feststeht (er haengt davon ab, ob ein System-Python verwendet wurde).
; Im Startmenue landen die beiden Eintraege, die ohne diese Kenntnis auskommen.
[Icons]
Name: "{group}\Diktiertool starten"; Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""{app}\installscript\windows\start.ps1"" -Hidden"
Name: "{group}\Diktiertool starten (mit Meldungen)"; Filename: "powershell.exe"; \
    Parameters: "-NoProfile -NoExit -ExecutionPolicy Bypass -File ""{app}\installscript\windows\start.ps1"""
Name: "{group}\Deinstallieren"; Filename: "{uninstallexe}"

; "64bit" schaltet fuer diesen Aufruf die WOW64-Dateisystem-Umleitung ab, damit
; wirklich die 64-Bit-PowerShell startet (siehe Kommentar bei
; ArchitecturesInstallIn64BitMode oben).
[Run]
Filename: "powershell.exe"; \
    Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\installscript\windows\bootstrap.ps1"" -InstallDir ""{app}"""; \
    StatusMsg: "Diktiertool wird eingerichtet (Python, Abhaengigkeiten) - das kann einige Minuten dauern ..."; \
    Flags: runascurrentuser waituntilterminated 64bit

; Ohne das kennt Inno Setup nur die fuenf .ps1-Dateien aus [Files] - der
; ZIP-Download, pip und der Modell-Zwischenspeicher legen tausende weitere
; Dateien in {app} an, die Inno nie registriert hat. Der eingebaute
; Deinstaller scheitert dann lautlos mit "Failed to delete directory (145)"
; und meldet trotzdem Erfolg. "filesandordirs" entfernt {app} rekursiv.
; Die Diktate liegen ausserhalb (Dokumente\Diktiertool) und bleiben erhalten.
[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
// Faengt einen zu langen Zielordner schon im Assistenten ab, statt die
// Einrichtung spaeter mittendrin scheitern zu lassen (siehe die
// gleichlautende Pruefung in install.ps1: onnxruntime legt unterhalb des
// Installationsordners Pfade von rund 135 Zeichen an, und Windows erlaubt
// ohne aktivierte Long-Path-Unterstuetzung nur 260 Zeichen insgesamt).
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    if Length(WizardDirValue) > 100 then
    begin
      MsgBox('Der gewaehlte Ordner ist mit ' + IntToStr(Length(WizardDirValue)) +
             ' Zeichen zu lang.' + #13#10 + #13#10 +
             'Windows erlaubt pro Datei insgesamt nur 260 Zeichen, und die ' +
             'Spracherkennung bringt darunter noch tief verschachtelte Ordner mit. ' +
             'Bitte einen kuerzeren Ordner waehlen (hoechstens 100 Zeichen).',
             mbError, MB_OK);
      Result := False;
    end;
  end;
end;

// Beendet ein laufendes Diktiertool und raeumt die per Skript angelegte
// Desktop-Verknuepfung weg, bevor Inno den Ordner loescht. Als Exec() in
// [Code] statt als [UninstallRun]-Eintrag, damit vor dem Loeschen des Ordners
// tatsaechlich gewartet wird.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
  ScriptPath: string;
begin
  if CurUninstallStep = usUninstall then
  begin
    ScriptPath := ExpandConstant('{app}\installscript\windows\uninstall.ps1');
    if not FileExists(ScriptPath) then
      Exit;

    // {sysnative} statt {sys}: der Deinstaller ist wie Setup.exe ein
    // 32-Bit-Prozess (siehe Kommentar bei ArchitecturesInstallIn64BitMode).
    Exec(ExpandConstant('{sysnative}\WindowsPowerShell\v1.0\powershell.exe'),
      '-NoProfile -ExecutionPolicy Bypass -File "' + ScriptPath + '"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox(
      'Das Diktiertool ist eingerichtet.' + #13#10 + #13#10 +
      'Starten ueber das Symbol auf dem Desktop oder den Eintrag im Startmenue.' + #13#10 + #13#10 +
      'Beim allerersten Start wird einmalig das Spracherkennungsmodell geladen ' +
      '(etwa 500 MB) - das dauert ein paar Minuten, der Status im Fenster zeigt ' +
      'es an und der Start-Knopf ist so lange gesperrt. Danach geht es in Sekunden.' + #13#10 + #13#10 +
      'Der erkannte Text wird fortlaufend in Dokumente\Diktiertool\diktat.txt gespeichert.',
      mbInformation, MB_OK);
  end;
end;
