#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

MISSING=""

if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
    MISSING="${MISSING}python3-venv "
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    MISSING="${MISSING}python3-tk "
fi

if ! ldconfig -p 2>/dev/null | grep libportaudio >/dev/null; then
    MISSING="${MISSING}libportaudio2 "
fi

if [ -n "$MISSING" ]; then
    echo "Folgende System-Pakete fehlen (keine pip-Pakete, muessen einmalig per apt installiert werden):"
    echo ""
    echo "    sudo apt install ${MISSING}"
    echo ""
    echo "Danach setup.sh erneut ausfuehren."
    exit 1
fi

if [ ! -d venv ]; then
    echo "Lege virtuelle Python-Umgebung an..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Setup abgeschlossen. Starte das Tool ab jetzt mit: ./start.sh"
