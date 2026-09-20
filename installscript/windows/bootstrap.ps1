#Requires -Version 5.1
<#
Diktiertool - Einstieg fuer einen frischen Windows-Rechner.

Windows-Pendant zu ../bootstrap.sh: holt den aktuellen Stand des Repos in ein
Zielverzeichnis und startet dort install.ps1, das den Rest erledigt. Ist der
Ordner schon da, wird er aktualisiert statt neu geholt.

Anders als unter Linux braucht es dafuer weder die GitHub CLI noch eine
Anmeldung - das Repo ist oeffentlich, das ZIP laedt jeder ohne Konto.

Aufruf (z.B. aus dem [Run]-Schritt von setup.iss):
  powershell -ExecutionPolicy Bypass -File bootstrap.ps1 -InstallDir "C:\Users\...\Diktiertool"
#>

[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "Diktiertool"),
    [string]$ZipUrl = "https://github.com/CrazyJimPro/diktiertool/archive/refs/heads/main.zip",
    [switch]$SkipShortcuts
)

$ErrorActionPreference = "Stop"

# Siehe install.ps1 - dieselben zwei Gruende (TLS-1.2-Aushandlung unter
# PowerShell 5.1, Fortschrittsbalken bremst grosse Downloads aus).
try {
    [Net.ServicePointManager]::SecurityProtocol =
        [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch { }
$ProgressPreference = "SilentlyContinue"

# Holt den aktuellen Stand als ZIP von GitHub und legt ihn ueber $InstallDir.
# python-runtime\, model-cache\ und install.log liegen nicht im ZIP und bleiben
# dabei unangetastet - eine Aktualisierung laedt also weder Python noch das
# Spracherkennungsmodell erneut herunter.
function Copy-RepoFromZip {
    param([string]$ZipUrl, [string]$InstallDir)

    $zipPath = Join-Path $env:TEMP "diktiertool-$([guid]::NewGuid()).zip"
    $extractDir = Join-Path $env:TEMP "diktiertool-extract-$([guid]::NewGuid())"

    Invoke-WebRequest -Uri $ZipUrl -OutFile $zipPath -UseBasicParsing
    Expand-Archive -Path $zipPath -DestinationPath $extractDir
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

    # GitHubs ZIP entpackt in einen Unterordner "diktiertool-<branch>" - dessen
    # Inhalt wird ins (ggf. schon vorhandene) Zielverzeichnis gemergt.
    $extractedRoot = Get-ChildItem $extractDir -Directory | Select-Object -First 1
    if (-not $extractedRoot) {
        Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
        throw "Das heruntergeladene ZIP war leer oder unerwartet aufgebaut ($ZipUrl)."
    }
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Copy-Item -Path (Join-Path $extractedRoot.FullName "*") -Destination $InstallDir -Recurse -Force
    Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue
}

try {
    New-Item -ItemType Directory -Path $InstallDir -Force -ErrorAction SilentlyContinue | Out-Null
    Start-Transcript -Path (Join-Path $InstallDir "install.log") -Append -ErrorAction SilentlyContinue | Out-Null
} catch {}

try {
    if (Test-Path (Join-Path $InstallDir ".git")) {
        # Von Hand per git geklont (Entwicklungsrechner) - dann nicht mit einem
        # ZIP darueberbuegeln, das wuerde lokale Aenderungen stillschweigend
        # ueberschreiben und die Arbeitskopie vom Repo abkoppeln.
        Write-Host "$InstallDir ist eine Git-Arbeitskopie - der Code wird nicht angefasst."
    } else {
        Write-Host "Hole aktuellen Stand von GitHub ..."
        Copy-RepoFromZip -ZipUrl $ZipUrl -InstallDir $InstallDir
    }

    $installScript = Join-Path $InstallDir "installscript\windows\install.ps1"
    if (-not (Test-Path $installScript)) {
        throw "install.ps1 fehlt in $InstallDir - der Download ist unvollstaendig."
    }

    # Hashtable, kein Array: ein gesplattetes Array uebergibt seine Elemente
    # POSITIONAL, der Name landet also als Wert im ersten Parameter
    # (-InstallDir bekaeme woertlich "-InstallDir") und ein Schalter wie
    # -NoTranscript bleibt als ueberzaehliges Argument uebrig, woraufhin
    # PowerShell mit "Es wurde kein Positionsparameter gefunden" abbricht.
    $arguments = @{ InstallDir = $InstallDir; NoTranscript = $true }
    if ($SkipShortcuts) { $arguments["SkipShortcuts"] = $true }
    & $installScript @arguments
} finally {
    try { Stop-Transcript -ErrorAction SilentlyContinue | Out-Null } catch {}
}
