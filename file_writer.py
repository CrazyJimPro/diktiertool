import os
from datetime import datetime
from pathlib import Path

from config import OUTPUT_FILE


class FileWriter:
    """Hängt erkannten Text an die Ausgabedatei an. Jeder Schreibvorgang wird sofort
    geflusht und ge-fsynct, damit bei einem Absturz nichts vom bereits Gesprochenen
    verloren geht."""

    def __init__(self, path: Path = OUTPUT_FILE):
        self.path = path

    def start_session(self):
        header = f"\n--- {datetime.now().strftime('%Y-%m-%d %H:%M')} ---\n"
        self._append(header)

    def write(self, text: str):
        self._append(text + "\n")

    def _append(self, text: str):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
