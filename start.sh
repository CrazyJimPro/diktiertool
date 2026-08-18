#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -d venv ]; then
    echo "Bitte zuerst ./setup.sh ausführen."
    exit 1
fi

source venv/bin/activate
python main.py
