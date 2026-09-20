#Requires -Version 5.1
<#
Diktiertool - Aufraeumen vor der Deinstallation.

Wird von setup.iss aufgerufen, bevor Inno Setup den Installationsordner
entfernt. Aufgabe: das laufende Programm beenden und die Verknuepfungen
loeschen, die install.ps1 per Skript angelegt hat (Inno kennt die nicht, weil
sie nicht aus seinem [Icons]-Abschnitt stammen).

Die Diktate selbst liegen unter Dokumente\Diktiertool und werden hier
ausdruecklich NICHT angefasst - das ist das einzige am ganzen Programm, was
sich nicht wiederherstellen laesst.
#>

[CmdletBinding()]
param(
    [string]$InstallDir
)

# Ein Fehler beim Aufraeumen darf die Deinstallation nicht anhalten.
$ErrorActionPreference = "Continue"

# Siehe start.ps1: als Standardwert im param()-Block oben waere $PSScriptRoot
# beim Aufruf ueber "powershell.exe -File ..." noch leer - und genau so ruft
# setup.iss dieses Skript bei der Deinstallation auf.
if (-not $InstallDir) {
    $InstallDir = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
}

# Laeuft das Tool gerade, haelt es Dateien im Installationsordner offen und
# Inno koennte ihn nicht vollstaendig loeschen. Getroffen werden nur
# Python-Prozesse aus genau diesem Ordner - ein zufaellig parallel laufendes
# anderes Python-Programm bleibt unberuehrt.
Get-Process -Name "python", "pythonw" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($InstallDir, [StringComparison]::OrdinalIgnoreCase) } |
    ForEach-Object {
        Write-Host "Beende laufendes Diktiertool (PID $($_.Id)) ..."
        try { $_.Kill() } catch { }
    }

$desktop = [Environment]::GetFolderPath("Desktop")
if ($desktop) {
    $shortcut = Join-Path $desktop "Diktiertool.lnk"
    if (Test-Path $shortcut) {
        Remove-Item $shortcut -Force -ErrorAction SilentlyContinue
        Write-Host "Desktop-Verknuepfung entfernt."
    }
}

Write-Host "Aufgeraeumt. Die Diktate in Dokumente\Diktiertool bleiben erhalten."
exit 0
