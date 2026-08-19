#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
PROJECT_DIR="$(pwd)"

APPS_DIR="$HOME/.local/share/applications"
mkdir -p "$APPS_DIR"
APPS_FILE="$APPS_DIR/diktiertool.desktop"

cat > "$APPS_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Diktiertool
Comment=Lokales Diktiergeraet mit Spracherkennung
Exec=$PROJECT_DIR/start.sh
Icon=audio-input-microphone
Terminal=false
Categories=AudioVideo;
EOF
chmod +x "$APPS_FILE"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo "Verknuepfung im Anwendungsmenue angelegt: $APPS_FILE"

DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
if [ -n "$DESKTOP_DIR" ] && [ -d "$DESKTOP_DIR" ]; then
    DESKTOP_FILE="$DESKTOP_DIR/diktiertool.desktop"
    cp "$APPS_FILE" "$DESKTOP_FILE"
    chmod +x "$DESKTOP_FILE"
    command -v gio >/dev/null 2>&1 && gio set "$DESKTOP_FILE" metadata::trusted true 2>/dev/null || true
    echo "Verknuepfung auf dem Desktop angelegt: $DESKTOP_FILE"
    echo "Falls ein Doppelklick dort zunaechst nur eine Warnung zeigt: einmal rechtsklicken -> 'Start erlauben' (Nautilus-Vertrauensmechanismus)."
fi
