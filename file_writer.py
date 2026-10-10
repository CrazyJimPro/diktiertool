import os
from datetime import datetime
from pathlib import Path

from config import OUTPUT_FILE

DEFAULT_OUTPUT_DIR = OUTPUT_FILE.parent


class FileWriter:
    """Hängt erkannten Text an die Ausgabedatei an. Jeder Schreibvorgang wird sofort
    geflusht und ge-fsynct, damit bei einem Absturz nichts vom bereits Gesprochenen
    verloren geht.

    Ordner und Dateiname werden erst bei start_session() aus den Einstellungen
    bestimmt - eine Aenderung im Dialog gilt also ab der naechsten Aufnahme,
    eine laufende schreibt in ihre Datei weiter."""

    def __init__(self, settings):
        self.settings = settings
        self.path: Path | None = None

    def output_dir(self) -> Path:
        custom = self.settings.get("output_dir")
        return Path(custom) if custom else DEFAULT_OUTPUT_DIR

    def start_session(self) -> str | None:
        """Gibt eine Warnung zurueck, wenn der gewaehlte Ordner nicht
        beschreibbar war und deshalb in den Standardordner geschrieben wird."""
        now = datetime.now()
        per_session = self.settings.get("file_per_session")
        name = f"diktat_{now:%Y-%m-%d_%H-%M}.txt" if per_session else OUTPUT_FILE.name
        header = f"\n--- {now.strftime('%Y-%m-%d %H:%M')} ---\n"

        folder = self.output_dir()
        try:
            self._open(folder / name, header, per_session)
            return None
        except OSError as exc:
            # Z. B. USB-Stick abgezogen oder Netzlaufwerk weg. Den Standardordner
            # (unter Windows in Dokumente) gibt es dagegen praktisch immer.
            if folder == DEFAULT_OUTPUT_DIR:
                raise
            self._open(DEFAULT_OUTPUT_DIR / name, header, per_session)
            return (f"Ausgabeordner nicht beschreibbar ({exc.strerror or exc}) – "
                    f"schreibe stattdessen nach {DEFAULT_OUTPUT_DIR}")

    def _open(self, path: Path, header: str, per_session: bool):
        # Unter Windows liegt die Datei in Dokumente\Diktiertool - ein Ordner,
        # den es beim allerersten Start noch nicht gibt.
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        # Eine eigene Datei pro Aufnahme traegt Datum und Uhrzeit schon im
        # Namen. Nur wenn zwei Aufnahmen in dieselbe Minute fallen, landet die
        # zweite mit Trenner in derselben Datei.
        if per_session and not (path.exists() and path.stat().st_size > 0):
            header = header.lstrip("\n")
        self._append(header)

    def write(self, text: str):
        if self.path is not None:
            self._append(text + "\n")

    def _append(self, text: str):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
