#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "Das System-Paket 'python3-tk' fehlt (wird fuer die GUI benoetigt, ist kein pip-Paket)."
    echo "Bitte einmalig ausfuehren und dann setup.sh erneut starten:"
    echo ""
    echo "    sudo apt install python3-tk"
    echo ""
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
