#Requires -Version 5.1
<#
Diktiertool - Einrichtung unter Windows.

Windows-Pendant zu ../../setup.sh: richtet eine portable Python-Umgebung im
Projektordner ein und installiert dort die Abhaengigkeiten aus
requirements.txt. Anders als unter Linux muss dafuer nichts per Paketverwaltung
nachinstalliert werden - PortAudio steckt im sounddevice-Wheel, und die Rolle
von GTK/WebKit2 uebernimmt die WebView2-Runtime, die in Windows 11 enthalten
ist (wird unten geprueft und notfalls nachinstalliert).

Aufruf:
  powershell -ExecutionPolicy Bypass -File install.ps1 -InstallDir "C:\Users\...\Diktiertool"
#>

[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Diktiertool"),
    # Muss zu den Wheels passen, die es fuer ctranslate2/numpy gibt. 3.12 ist
    # die Version, mit der das Tool getestet ist.
    [string]$PythonVersion = "3.12.10",
    [switch]$SkipShortcuts,
    # Gesetzt von bootstrap.ps1, das bereits in dieselbe Datei protokolliert -
    # ein zweites, verschachteltes Start-Transcript schlaegt in Windows
    # PowerShell 5.1 fehl, und das passende Stop-Transcript wuerde dann das
    # aeussere Protokoll vorzeitig beenden.
    [switch]$NoTranscript
)

$ErrorActionPreference = "Stop"

# TLS 1.2 muss unter Windows PowerShell 5.1 ausdruecklich eingeschaltet werden,
# sonst scheitert schon der Download von python.org. Der Fortschrittsbalken
# bremst grosse Downloads in 5.1 massiv aus (Faktor 10 und mehr).
try {
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch { }
$ProgressPreference = "SilentlyContinue"

. (Join-Path $PSScriptRoot "find-python.ps1")

# Persistentes Log: der [Run]-Schritt von Inno Setup faengt die
# Konsolenausgabe nicht ein und zeigt bei einem Fehler nur "fertig" ohne jeden
# Hinweis. Mit Transcript bleibt immer nachvollziehbar, was passiert ist.
if (-not $NoTranscript) {
    try {
        New-Item -ItemType Directory -Path $InstallDir -Force -ErrorAction SilentlyContinue | Out-Null
        Start-Transcript -Path (Join-Path $InstallDir "install.log") -Append -ErrorAction SilentlyContinue | Out-Null
    } catch {}
}

# Die Evergreen-WebView2-Runtime ist auf Windows 11 vorinstalliert, auf
# aelteren Windows-10-Staenden nicht zwingend. Ohne sie faellt pywebview auf
# das uralte MSHTML-Backend zurueck, das vom Design der Oberflaeche nichts
# uebrig laesst (kein backdrop-filter, keine modernen Verlaeufe).
function Test-WebView2Installed {
    $clientKeys = @(
        "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        "HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    )
    foreach ($key in $clientKeys) {
        if (Test-Path $key) {
            $version = (Get-ItemProperty $key -ErrorAction SilentlyContinue).pv
            if ($version -and $version -ne "0.0.0.0") { return $true }
        }
    }
    return $false
}

function Install-WebView2 {
    Write-Host "WebView2-Runtime fehlt, wird nachinstalliert ..."
    $installer = Join-Path $env:TEMP "MicrosoftEdgeWebview2Setup.exe"
    Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/p/?LinkId=2124703" -OutFile $installer -UseBasicParsing
    # /silent /install laeuft ohne Adminrechte als Benutzerinstallation durch.
    $process = Start-Process -FilePath $installer -ArgumentList "/silent", "/install" -Wait -PassThru
    Remove-Item $installer -Force -ErrorAction SilentlyContinue
    if ($process.ExitCode -ne 0) {
        Write-Warning "Die WebView2-Installation meldete Code $($process.ExitCode). Das Tool startet moeglicherweise mit einer aelteren Darstellung."
    }
}

# Die ._pth-Datei des embeddable package legt sys.path abschliessend fest - und
# zwar wirklich abschliessend: sie schaltet nebenbei die uebliche Regel ab, dass
# der Ordner des gestarteten Skripts automatisch im Suchpfad landet. Zwei
# Ergaenzungen sind deshalb noetig:
#   "import site" + "Lib\site-packages" -> pip findet seine eigenen Pakete
#       (sonst scheitert schon das Einrichten mit "No module named pip")
#   ".."  -> der Projektordner eine Ebene ueber python-runtime\, in dem gui.py,
#       config.py und der Rest liegen (sonst startet main.py mit
#       "No module named 'gui'")
# Die Eintraege sind relativ zum Ordner der ._pth-Datei.
#
# Laeuft bei jeder Einrichtung, nicht nur beim erstmaligen Entpacken: bei einer
# Aktualisierung bleibt ein vorhandenes python-runtime\ stehen, und eine von
# einer aelteren Fassung dieses Skripts angelegte, unvollstaendige ._pth wuerde
# sonst nie korrigiert.
function Repair-PythonPath {
    param([string]$RuntimeDir)

    $pthFile = Get-ChildItem $RuntimeDir -Filter "python*._pth" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $pthFile) {
        # Kein ._pth heisst: kein embeddable package, sondern ein normales
        # Python - dort gelten die ueblichen sys.path-Regeln und es gibt nichts
        # zu reparieren.
        return
    }

    $content = (Get-Content $pthFile.FullName) -replace '^\s*#\s*import site\s*$', 'import site'
    if ($content -notcontains 'Lib\site-packages') { $content += 'Lib\site-packages' }
    if ($content -notcontains '..') { $content += '..' }
    Set-Content -Path $pthFile.FullName -Value $content -Encoding Ascii
}

# Holt das offizielle "embeddable package" von python.org - eine ZIP-Datei mit
# einem vollstaendigen, portablen Python (~11MB), das sich nirgends im System
# eintraegt. Deshalb auch kein venv: dieser Ordner IST die abgeschottete
# Umgebung.
function Install-PortablePython {
    param([string]$TargetDir, [string]$Version)

    $zipUrl = "https://www.python.org/ftp/python/$Version/python-$Version-embed-amd64.zip"
    $zipPath = Join-Path $env:TEMP "python-embed-$Version.zip"

    Write-Host "Lade portables Python $Version ..."
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
    if (Test-Path $TargetDir) { Remove-Item $TargetDir -Recurse -Force }
    Expand-Archive -Path $zipPath -DestinationPath $TargetDir -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

    Repair-PythonPath -RuntimeDir $TargetDir

    Write-Host "Richte pip ein ..."
    $getPip = Join-Path $TargetDir "get-pip.py"
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
    & (Join-Path $TargetDir "python.exe") $getPip --no-warn-script-location
    if ($LASTEXITCODE -ne 0) { throw "pip liess sich nicht einrichten (Code $LASTEXITCODE)." }
    Remove-Item $getPip -Force -ErrorAction SilentlyContinue
}

# Verknuepfungen zeigen direkt auf pythonw.exe: das ist die fensterlose
# Variante des Interpreters, damit beim Start kein schwarzes Konsolenfenster
# aufblitzt und waehrend der Laufzeit keines offen bleibt. Ein Umweg ueber eine
# .bat oder .vbs ist dafuer nicht noetig.
function New-Shortcut {
    param([string]$Path, [string]$TargetExe, [string]$Arguments, [string]$WorkingDir, [string]$IconLocation)

    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = $TargetExe
    $shortcut.Arguments = $Arguments
    $shortcut.WorkingDirectory = $WorkingDir
    $shortcut.Description = "Lokales Diktiergeraet mit Spracherkennung"
    if ($IconLocation) { $shortcut.IconLocation = $IconLocation }
    $shortcut.Save()
}

try {
    if (-not (Test-Path (Join-Path $InstallDir "requirements.txt"))) {
        throw "In $InstallDir liegt kein Diktiertool (requirements.txt fehlt). Zuerst bootstrap.ps1 ausfuehren."
    }

    # Windows bricht Dateioperationen jenseits von 260 Zeichen ab, solange die
    # Long-Path-Unterstuetzung nicht aktiv ist. onnxruntime (kommt als
    # Abhaengigkeit von faster-whisper mit) bringt Pfade von rund 135 Zeichen
    # Laenge unterhalb von python-runtime\ mit - ab etwa 120 Zeichen
    # Installationspfad scheitert pip deshalb mitten im Entpacken, mit einem
    # nichtssagenden "[Errno 2] No such file or directory". Lieber vorher
    # verstaendlich abbrechen, bevor 200MB umsonst geladen werden.
    if ($InstallDir.Length -gt 100) {
        throw ("Der Installationspfad ist mit $($InstallDir.Length) Zeichen zu lang: $InstallDir`n" +
               "Windows erlaubt insgesamt nur 260 Zeichen pro Datei, und die Pakete legen darunter " +
               "noch tief verschachtelte Ordner an. Bitte einen kuerzeren Zielordner waehlen, " +
               "z.B. den Vorschlag %LOCALAPPDATA%\Diktiertool.")
    }

    if (Test-WebView2Installed) {
        Write-Host "WebView2-Runtime ist vorhanden."
    } else {
        Install-WebView2
    }

    $runtimeDir = Join-Path $InstallDir "python-runtime"
    $python = Find-PythonBin -ProjectDir $InstallDir

    if (-not $python) {
        # Bewusst kein Rueckgriff auf ein Python aus dem PATH, auch wenn eines
        # da ist - Begruendung in find-python.ps1.
        Install-PortablePython -TargetDir $runtimeDir -Version $PythonVersion
        $python = Join-Path $runtimeDir "python.exe"
    } else {
        Write-Host "Portables Python ist bereits eingerichtet: $python"
        Repair-PythonPath -RuntimeDir $runtimeDir
    }

    Write-Host "Installiere Abhaengigkeiten (faster-whisper, sounddevice, pywebview) ..."
    & $python -m pip install --upgrade pip --no-warn-script-location
    & $python -m pip install --no-warn-script-location -r (Join-Path $InstallDir "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "Die Installation der Abhaengigkeiten ist fehlgeschlagen (Code $LASTEXITCODE)." }

    # Siehe transcriber.py: existiert dieser Ordner, landet das
    # Spracherkennungsmodell darin statt in %USERPROFILE%\.cache\huggingface -
    # und wird bei der Deinstallation restlos mitentfernt.
    New-Item -ItemType Directory -Path (Join-Path $InstallDir "model-cache") -Force | Out-Null

    & $python -c "import sounddevice, faster_whisper, webview"
    if ($LASTEXITCODE -ne 0) { throw "Die installierten Pakete lassen sich nicht laden - siehe install.log." }
    Write-Host "Alle Pakete geladen."

    if (-not $SkipShortcuts) {
        $pythonw = Find-PythonwBin -ProjectDir $InstallDir
        $desktop = [Environment]::GetFolderPath("Desktop")
        if ($desktop) {
            New-Shortcut -Path (Join-Path $desktop "Diktiertool.lnk") -TargetExe $pythonw `
                -Arguments "main.py" -WorkingDir $InstallDir -IconLocation "$pythonw,0"
            Write-Host "Verknuepfung auf dem Desktop angelegt."
        }
    }

    Write-Host ""
    Write-Host "Einrichtung abgeschlossen."
} finally {
    if (-not $NoTranscript) {
        try { Stop-Transcript -ErrorAction SilentlyContinue | Out-Null } catch {}
    }
}
