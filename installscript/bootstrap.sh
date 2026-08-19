#!/usr/bin/env bash
set -euo pipefail

REPO="CrazyJimPro/diktiertool"
TARGET_DIR="${DIKTIERTOOL_DIR:-$HOME/diktiertool}"

if ! command -v gh >/dev/null 2>&1; then
    echo "GitHub CLI (gh) fehlt, installiere sie..."
    (type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
        && sudo mkdir -p -m 755 /etc/apt/keyrings \
        && wget -nv -O- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
        && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
        && sudo mkdir -p -m 755 /etc/apt/sources.list.d \
        && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
        && sudo apt update \
        && sudo apt install gh -y
fi

if ! gh auth status >/dev/null 2>&1; then
    echo "Nicht bei GitHub angemeldet, starte Login..."
    gh auth login --web
fi

if [ -d "$TARGET_DIR" ]; then
    echo "$TARGET_DIR existiert bereits, ueberspringe Klonen."
else
    echo "Klone $REPO nach $TARGET_DIR..."
    gh repo clone "$REPO" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
./setup.sh

echo ""
echo "Fertig. Starte das Tool ab jetzt mit: cd $TARGET_DIR && ./start.sh"
