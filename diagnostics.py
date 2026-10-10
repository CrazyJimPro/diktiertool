r"""Diagnose: Logdatei, aufgehobene Fehl-Aufnahmen und Pegelanhebung.

Das Log enthaelt nie erkannten Text - nur Messwerte (Dauer, Pegel, wie viele
Segmente aus welchem Grund verworfen wurden, Rechenzeit). So laesst es sich
gefahrlos weitergeben, wenn etwas nicht klappt.

Ort: Windows %LOCALAPPDATA%\Diktiertool\logs, Linux ~/.local/state/diktiertool/logs.
Nicht neben den Einstellungen in %APPDATA% (Roaming): Logs und Audiodateien
haben in einem servergespeicherten Profil nichts verloren."""

import logging
import logging.handlers
import os
import sys
import threading
import traceback
import wave
from datetime import datetime
from pathlib import Path

import numpy as np


def _log_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / "Diktiertool" / "logs"
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / "diktiertool" / "logs"


LOG_DIR = _log_dir()
FAILED_DIR = LOG_DIR / "fehlaufnahmen"
MAX_FAILED_RECORDINGS = 3

log = logging.getLogger("diktiertool")

# Pegelanhebung: leise Mikrofone liefern Sprache mit Spitzen weit unter
# Vollaussteuerung, und Whisper erkennt solche Haeppchen spuerbar schlechter.
# Angehoben wird auf eine Spitze von 0.5 (nicht 1.0 - Luft fuer Ausreisser),
# hoechstens um Faktor 30, damit reines Rauschen nicht zu "Sprache" wird.
TARGET_PEAK = 0.5
MAX_GAIN = 30.0


def setup():
    """Logdatei einrichten. Scheitert das (Ordner nicht anlegbar), laeuft das
    Programm ohne Log weiter - Diagnose darf nie der Grund fuer einen
    Absturz sein."""
    log.setLevel(logging.INFO)
    log.propagate = False
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "diktiertool.log", maxBytes=512 * 1024, backupCount=3, encoding="utf-8",
        )
    except OSError:
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(message)s",
                                           "%Y-%m-%d %H:%M:%S"))
    log.addHandler(handler)

    # Unbehandelte Fehler landen sonst nur auf einer Konsole, die es beim
    # Start per Desktop-Symbol (pythonw) gar nicht gibt.
    def excepthook(exc_type, exc, tb):
        log.error("Unbehandelter Fehler:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
        sys.__excepthook__(exc_type, exc, tb)

    def thread_excepthook(args):
        log.error("Unbehandelter Fehler im Thread %s:\n%s", args.thread.name if args.thread else "?",
                  "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))

    sys.excepthook = excepthook
    threading.excepthook = thread_excepthook


def normalize_gain(audio: np.ndarray) -> tuple[np.ndarray, float]:
    """Leises Audio auf TARGET_PEAK anheben. Liefert (Audio, Faktor)."""
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak <= 0.0 or peak >= TARGET_PEAK:
        return audio, 1.0
    gain = min(TARGET_PEAK / peak, MAX_GAIN)
    return (audio * gain).astype(np.float32), gain


def save_failed_recording(audio: np.ndarray, sample_rate: int) -> Path | None:
    """Haeppchen, aus dem kein Text wurde, als WAV ablegen - nur die letzten
    MAX_FAILED_RECORDINGS bleiben, aeltere werden geloescht."""
    try:
        FAILED_DIR.mkdir(parents=True, exist_ok=True)
        # Millisekunden im Namen: zwei Fehl-Haeppchen kurz nacheinander duerfen
        # sich nicht ueberschreiben; Namen sortieren sich chronologisch.
        name = datetime.now().strftime("fehlaufnahme_%Y-%m-%d_%H-%M-%S-%f")[:-3] + ".wav"
        path = FAILED_DIR / name
        pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm.tobytes())
        prune_failed_recordings()
        return path
    except OSError as exc:
        log.warning("Fehl-Aufnahme nicht gespeichert: %s", exc)
        return None


def prune_failed_recordings(keep: int = MAX_FAILED_RECORDINGS):
    try:
        files = sorted(FAILED_DIR.glob("fehlaufnahme_*.wav"))
    except OSError:
        return
    for old in files[:-keep] if keep else files:
        try:
            old.unlink()
        except OSError:
            pass
