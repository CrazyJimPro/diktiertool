r"""Einstellungen, die der Benutzer in der Oberflaeche aendert. config.py liefert
nur die Vorgaben.

Die Datei liegt bewusst nicht im Programmordner: unter Windows ersetzt ein
Installer-Update %LOCALAPPDATA%\Diktiertool, unter Linux wuerde sie bei
"git pull" im Weg liegen."""

import json
import os
import sys
import threading
from pathlib import Path


def _settings_file() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "Diktiertool" / "settings.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "diktiertool" / "settings.json"


SETTINGS_FILE = _settings_file()

DEFAULTS = {
    # Geraetename ohne "[idx]" - der Index aendert sich, sobald ein Geraet
    # an- oder abgesteckt wird.
    "device_name": None,
    "punctuation_commands": False,
}


class Settings:
    def __init__(self, path: Path = SETTINGS_FILE):
        self.path = path
        self._lock = threading.Lock()
        self._values = dict(DEFAULTS)
        self._load()

    def _load(self):
        # Kaputte oder von Hand verbogene Datei darf den Start nie verhindern -
        # dann eben mit Vorgaben weiter.
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if isinstance(data, dict):
            for key, value in data.items():
                if key in DEFAULTS:
                    self._values[key] = value

    def get(self, key):
        with self._lock:
            return self._values[key]

    def update(self, **changes):
        with self._lock:
            self._values.update({k: v for k, v in changes.items() if k in DEFAULTS})
            snapshot = dict(self._values)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            pass  # Nicht speichern koennen ist aergerlich, aber kein Grund abzustuerzen
