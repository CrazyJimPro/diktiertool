# Gemeinsame Python-Aufloesung, per Dot-Source von install.ps1 und start.ps1
# eingebunden. Windows-Pendant zu dem, was setup.sh unter Linux mit der venv
# macht.
#
# Verwendet wird ausschliesslich die portable Python-Installation unter
# python-runtime\ im Projektordner (von install.ps1 angelegt) - nie ein
# Python aus dem PATH. Das ist der Unterschied zu einer Node-Anwendung, wo ein
# System-Node gefahrlos mitbenutzt werden kann, weil npm ohnehin projektlokal
# nach node_modules\ installiert: pip installiert in die globalen
# site-packages des jeweiligen Interpreters. Ein vorhandenes System-Python
# haette sich damit 30 Pakete eingefangen, die es nie angefordert hat - und
# die Deinstallation koennte sie nicht zuverlaessig wieder entfernen, weil
# nicht feststellbar ist, welche davon schon vorher gebraucht wurden.

function Test-PythonVersionOk {
    param([string]$PythonExe, [string]$MinVersion)

    if (-not (Test-Path $PythonExe)) { return $false }
    try {
        $raw = & $PythonExe -c "import sys; print('%d.%d.%d' % sys.version_info[:3])" 2>$null
    } catch {
        return $false
    }
    if (-not $raw) { return $false }

    try {
        return ([version]$raw.Trim()) -ge ([version]$MinVersion)
    } catch {
        return $false
    }
}

# Gibt den Pfad zum portablen python.exe zurueck, oder $null, wenn es noch
# keines gibt (dann legt install.ps1 eines an).
# Aufruf: Find-PythonBin -ProjectDir $ProjectDir -MinVersion "3.10.0"
function Find-PythonBin {
    param([string]$ProjectDir, [string]$MinVersion = "3.10.0")

    $portable = Join-Path $ProjectDir "python-runtime\python.exe"
    if (Test-PythonVersionOk $portable $MinVersion) { return $portable }

    return $null
}

# Das Gegenstueck fuers Starten ohne Konsolenfenster - pythonw.exe liegt im
# eingebetteten Python direkt neben python.exe.
function Find-PythonwBin {
    param([string]$ProjectDir, [string]$MinVersion = "3.10.0")

    $python = Find-PythonBin -ProjectDir $ProjectDir -MinVersion $MinVersion
    if (-not $python) { return $null }

    $pythonw = Join-Path (Split-Path $python -Parent) "pythonw.exe"
    if (Test-Path $pythonw) { return $pythonw }

    return $python
}
