"""Audiodateien einlesen und den Speicherort fuer das Transkript bestimmen.

Bewusst eine eigene Dekodierung statt faster_whisper.decode_audio: die ruft
av.open(..., metadata_errors="ignore") auf, und das kennen neuere
PyAV-Versionen nicht mehr (TypeError mit PyAV 19, das pip im Windows-Installer
mitbringt). Ein ffmpeg-Programm braucht es nicht - PyAV bringt die
Bibliotheken mit."""

import gc
import threading
from pathlib import Path

import av
import numpy as np

AUDIO_EXTENSIONS = (".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac", ".aac",
                    ".mp4", ".webm", ".wma")


class AudioFileError(Exception):
    """Meldung ist fuer die Statuszeile gedacht."""


def decode(path: Path, sample_rate: int, cancel: threading.Event | None = None) -> np.ndarray | None:
    """Datei -> float32-Mono mit sample_rate. None, wenn cancel gesetzt wurde."""
    try:
        container = av.open(str(path))
    except FileNotFoundError:
        raise AudioFileError("Datei nicht gefunden")
    except (av.error.FFmpegError, OSError) as exc:
        # strerror statt str(exc): das haengt noch den ganzen Pfad an, der in
        # der Statuszeile ohnehin schon mit dem Dateinamen steht
        raise AudioFileError(f"keine lesbare Audiodatei ({exc.strerror or exc})")

    chunks = []
    try:
        with container:
            if not container.streams.audio:
                raise AudioFileError("enthält keine Tonspur")
            resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=sample_rate)
            try:
                for frame in container.decode(audio=0):
                    if cancel is not None and cancel.is_set():
                        return None
                    for out in resampler.resample(frame):
                        chunks.append(out.to_ndarray().reshape(-1))
                for out in resampler.resample(None):  # Rest aus dem Resampler holen
                    chunks.append(out.to_ndarray().reshape(-1))
            except av.error.InvalidDataError:
                # Kaputtes Ende (abgebrochene Aufnahme o. ae.): alles bis dahin
                # ist brauchbar - genau wie faster-whisper es auch handhabt.
                pass
            finally:
                # Siehe faster_whisper.audio: ohne gc bleiben Teile des
                # Resamplers im Speicher haengen.
                del resampler
                gc.collect()
    except av.error.FFmpegError as exc:
        raise AudioFileError(f"lässt sich nicht dekodieren ({exc.strerror or exc})")

    if not chunks:
        raise AudioFileError("enthält keinen Ton")
    return np.concatenate(chunks).astype(np.float32) / 32768.0


def result_path(audio_path: Path, fallback_dir: Path) -> Path:
    """Transkript-Datei neben der Audiodatei, sonst im Ausgabeordner. Legt die
    Datei leer an (exklusiv - eine vorhandene wird nie ueberschrieben, dann
    heisst die neue "<name> (2).txt")."""
    for folder in (audio_path.parent, fallback_dir):
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            continue
        for n in range(1, 1000):
            suffix = "" if n == 1 else f" ({n})"
            candidate = folder / f"{audio_path.stem}{suffix}.txt"
            try:
                with open(candidate, "x", encoding="utf-8"):
                    return candidate
            except FileExistsError:
                continue
            except OSError:
                break  # Ordner nicht beschreibbar (CD, Netzlaufwerk nur lesend ...)
    raise AudioFileError("kein beschreibbarer Ordner für das Ergebnis gefunden")
