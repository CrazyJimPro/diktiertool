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

import config


def _settings_file() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "Diktiertool" / "settings.json"
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "diktiertool" / "settings.json"


SETTINGS_FILE = _settings_file()

MODEL_CHOICES = ("small", "medium", "large-v3-turbo")
LANGUAGE_CHOICES = ("de", "en", "auto")

DEFAULTS = {
    # Geraetename ohne "[idx]" - der Index aendert sich, sobald ein Geraet
    # an- oder abgesteckt wird.
    "device_name": None,
    "punctuation_commands": False,
    "model_size": config.MODEL_SIZE,
    "language": config.LANGUAGE,
    # None = Standardordner (Dokumente\Diktiertool bzw. Projektordner)
    "output_dir": None,
    "file_per_session": False,
    "vocabulary": [],
}


def _is_valid(key, value) -> bool:
    """Prueft Werte aus der Datei und aus der Oberflaeche gleichermassen - ein
    von Hand eingetragenes "vocabulary": "Meier" darf spaeter nicht als
    Buchstabenliste beim Modell ankommen."""
    if key == "model_size":
        return value in MODEL_CHOICES
    if key == "language":
        return value in LANGUAGE_CHOICES
    if key in ("device_name", "output_dir"):
        return value is None or (isinstance(value, str) and value != "")
    if key in ("punctuation_commands", "file_per_session"):
        return isinstance(value, bool)
    if key == "vocabulary":
        return isinstance(value, list) and all(isinstance(w, str) for w in value)
    return False


def parse_vocabulary(text: str) -> list[str]:
    """Eingabefeld -> Wortliste: eine Zeile oder ein Komma je Begriff,
    Leerzeichen und doppelte Eintraege fallen weg."""
    words = []
    for part in text.replace(",", "\n").split("\n"):
        word = " ".join(part.split())
        if word and word.casefold() not in (w.casefold() for w in words):
            words.append(word)
    return words


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
                if key in DEFAULTS and _is_valid(key, value):
                    self._values[key] = value

    def get(self, key):
        with self._lock:
            value = self._values[key]
        return list(value) if isinstance(value, list) else value

    def all(self) -> dict:
        with self._lock:
            return {k: list(v) if isinstance(v, list) else v for k, v in self._values.items()}

    def update(self, **changes):
        """Ungueltige Werte werden stillschweigend verworfen."""
        with self._lock:
            self._values.update(
                {k: v for k, v in changes.items() if k in DEFAULTS and _is_valid(k, v)}
            )
            snapshot = dict(self._values)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            pass  # Nicht speichern koennen ist aergerlich, aber kein Grund abzustuerzen
