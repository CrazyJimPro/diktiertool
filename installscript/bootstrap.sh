#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/CrazyJimPro/diktiertool.git"
TARGET_DIR="${DIKTIERTOOL_DIR:-$HOME/diktiertool}"

# Frueher lief das Klonen ueber die GitHub CLI samt "gh auth login --web",
# weil das Repo privat war. Seit es oeffentlich ist, reicht ein normales
# git clone - kein Konto, keine Anmeldung, kein einmaliger Code im Browser.
if ! command -v git >/dev/null 2>&1; then
    echo "git fehlt, installiere es..."
    sudo apt update && sudo apt install -y git
fi

if [ -d "$TARGET_DIR" ]; then
    echo "$TARGET_DIR existiert bereits, ueberspringe Klonen."
else
    echo "Klone $REPO_URL nach $TARGET_DIR..."
    git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
./setup.sh

echo ""
echo "Fertig. Starte das Tool ab jetzt mit: cd $TARGET_DIR && ./start.sh"
