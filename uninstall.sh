#!/usr/bin/env bash
# Entfernt alles, was setup.sh/install-desktop-entry.sh ausserhalb dieses
# Projektordners angelegt haben - Linux-Pendant zu
# installscript/windows/uninstall.ps1. Dort uebernimmt der Inno-Setup-
# Deinstaller das Loeschen des Installationsordners automatisch (inkl.
# Modell-Cache, der dort immer darin liegt); unter Linux liegt der
# Modell-Cache standardmaessig im geteilten ~/.cache/huggingface, deshalb hier
# gezielt per Namensmuster statt den ganzen Ordner zu leeren.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
PROJECT_DIR="$(pwd)"

# Laeuft das Tool gerade, beenden - sonst haelt es ggf. die Lock-Datei offen.
# Getroffen wird nur ein Prozess, der genau das venv-Python DIESES
# Projektordners nutzt, ein zufaellig parallel laufendes anderes
# Python-Programm bleibt unberuehrt.
PIDS="$(pgrep -f "$PROJECT_DIR/venv/bin/python" || true)"
if [ -n "$PIDS" ]; then
    echo "Beende laufendes Diktiertool ..."
    kill $PIDS 2>/dev/null || true
fi

removed=0

APPS_FILE="$HOME/.local/share/applications/diktiertool.desktop"
if [ -f "$APPS_FILE" ]; then
    rm -f "$APPS_FILE"
    echo "Menue-Verknuepfung entfernt."
    removed=1
fi

DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
if [ -n "$DESKTOP_DIR" ] && [ -f "$DESKTOP_DIR/diktiertool.desktop" ]; then
    rm -f "$DESKTOP_DIR/diktiertool.desktop"
    echo "Desktop-Verknuepfung entfernt."
    removed=1
fi

# settings.py bzw. single_instance.py (Lock-Datei, Weck-Port)
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/diktiertool"
if [ -d "$CONFIG_DIR" ]; then
    rm -rf "$CONFIG_DIR"
    echo "Einstellungen entfernt ($CONFIG_DIR)."
    removed=1
fi

# diagnostics.py: Log + aufgehobene Fehl-Aufnahmen
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/diktiertool"
if [ -d "$STATE_DIR" ]; then
    rm -rf "$STATE_DIR"
    echo "Diagnose-Log entfernt ($STATE_DIR)."
    removed=1
fi

# Spracherkennungsmodelle: eigener Parakeet-Ordner (siehe
# parakeet_engine.py::ensure_model) plus alle faster-whisper-Modelle im
# geteilten HF-Cache - gezielt per Namensmuster, damit nicht versehentlich
# Modelle anderer Tools im selben Cache-Ordner mitgeloescht werden.
HF_HOME_DIR="${HF_HOME:-$HOME/.cache/huggingface}"
if [ -d "$HF_HOME_DIR/parakeet-primeline-onnx" ]; then
    rm -rf "$HF_HOME_DIR/parakeet-primeline-onnx"
    echo "Parakeet-Modell entfernt."
    removed=1
fi
if [ -d "$HF_HOME_DIR/hub" ]; then
    for d in "$HF_HOME_DIR/hub"/models--*faster-whisper*; do
        [ -d "$d" ] || continue
        rm -rf "$d"
        echo "Whisper-Modell entfernt ($(basename "$d"))."
        removed=1
    done
fi

if [ "$removed" -eq 0 ]; then
    echo "Nichts zu entfernen gefunden - war wohl schon aufgeraeumt."
fi

echo ""
echo "Deine Diktate (diktat.txt bzw. dein gewaehlter Ausgabeordner) bleiben erhalten."
echo "Um auch den Programmordner samt virtueller Umgebung zu entfernen:"
echo ""
echo "    rm -rf \"$PROJECT_DIR\""
echo ""
echo "(Dieses Skript kann seinen eigenen Ordner nicht selbst loeschen, solange es noch laeuft.)"
