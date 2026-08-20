#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

MISSING=""

if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
    MISSING="${MISSING}python3-venv "
fi

if ! ldconfig -p 2>/dev/null | grep libportaudio >/dev/null; then
    MISSING="${MISSING}libportaudio2 "
fi

# GUI laeuft ueber pywebview (GTK/WebKit2-Backend) statt customtkinter - diese
# Bindings sind PyGObject, das ueblicherweise nicht zuverlaessig per pip
# installierbar ist, sondern als System-Paket kommt.
if ! python3 -c "import gi; gi.require_version('Gtk', '3.0'); gi.require_version('WebKit2', '4.1')" >/dev/null 2>&1; then
    MISSING="${MISSING}python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 "
fi

if [ -n "$MISSING" ]; then
    echo "Folgende System-Pakete fehlen (keine pip-Pakete, muessen einmalig per apt installiert werden):"
    echo ""
    echo "    sudo apt install ${MISSING}"
    echo ""
    echo "Danach setup.sh erneut ausfuehren."
    exit 1
fi

# Venv braucht Zugriff auf die System-gi-Bindings (siehe oben) - eine aeltere
# venv ohne --system-site-packages (vor dem Umstieg auf pywebview) wird hier
# erkannt und neu angelegt statt mit fehlendem gi-Zugriff weiterzulaufen.
if [ -d venv ] && ! venv/bin/python3 -c "import gi" >/dev/null 2>&1; then
    echo "Vorhandene venv hat keinen Zugriff auf die System-gi-Bindings, lege sie neu an..."
    rm -rf venv
fi

if [ ! -d venv ]; then
    echo "Lege virtuelle Python-Umgebung an..."
    python3 -m venv --system-site-packages venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

./install-desktop-entry.sh

echo ""
echo "Setup abgeschlossen. Starte das Tool ab jetzt mit: ./start.sh (oder ueber die neu angelegte Desktop-/Menue-Verknuepfung)"
