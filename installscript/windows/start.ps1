#Requires -Version 5.1
<#
Diktiertool starten - Windows-Pendant zu ../../start.sh.

Der Normalfall ist die Desktop-Verknuepfung, die direkt auf pythonw.exe zeigt
und ohne Konsolenfenster startet. Dieses Skript ist der Weg fuer den Fall, dass
etwas klemmt: es startet mit sichtbarer Konsole, so dass Fehlermeldungen
lesbar sind statt kommentarlos mit dem Fenster zu verschwinden.
#>

[CmdletBinding()]
param(
    [string]$InstallDir = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    # Startet wie die Verknuepfung ohne Konsolenfenster.
    [switch]$Hidden
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "find-python.ps1")

if ($Hidden) {
    $python = Find-PythonwBin -ProjectDir $InstallDir
} else {
    $python = Find-PythonBin -ProjectDir $InstallDir
}

if (-not $python) {
    Write-Error "In $InstallDir gibt es keine eingerichtete Python-Umgebung (python-runtime\ fehlt). Bitte zuerst install.ps1 ausfuehren."
    exit 1
}

Set-Location $InstallDir
& $python (Join-Path $InstallDir "main.py")
exit $LASTEXITCODE
