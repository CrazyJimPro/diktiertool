import ctypes
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent


def _windows_documents_dir() -> Path | None:
    """Echter Pfad des Dokumente-Ordners ueber die Windows-API. Nicht einfach
    ~/Documents: der Ordner kann per OneDrive umgeleitet sein (dann liegt er
    unter ~/OneDrive/Dokumente) oder vom Benutzer verschoben worden sein -
    SHGetKnownFolderPath liefert immer den tatsaechlichen Ort."""

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", ctypes.c_ulong),
            ("Data2", ctypes.c_ushort),
            ("Data3", ctypes.c_ushort),
            ("Data4", ctypes.c_byte * 8),
        ]

    # FOLDERID_Documents, siehe KnownFolders.h
    folder_id = GUID(
        0xFDD39AD0, 0x238F, 0x46AF,
        (ctypes.c_byte * 8)(*[0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7]),
    )
    buf = ctypes.c_wchar_p()
    try:
        if ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_id), 0, None, ctypes.byref(buf)
        ) != 0:
            return None
        path = buf.value
        ctypes.windll.ole32.CoTaskMemFree(buf)
        return Path(path) if path else None
    except (AttributeError, OSError):
        return None


def _default_output_file() -> Path:
    r"""Unter Linux liegt die Ausgabe wie gehabt direkt im Projektordner. Unter
    Windows installiert der Setup nach %LOCALAPPDATA%\Diktiertool - ein
    Programmordner, in dem niemand seine Diktate sucht (und den die
    Deinstallation mitsamt Inhalt entfernt). Dort landet der Text deshalb
    unter Dokumente\Diktiertool."""
    if sys.platform == "win32":
        documents = _windows_documents_dir() or (Path.home() / "Documents")
        if documents.is_dir():
            return documents / "Diktiertool" / "diktat.txt"
    return PROJECT_DIR / "diktat.txt"


OUTPUT_FILE = _default_output_file()

# Bei jedem Release manuell mit dem neuen Git-Tag synchron halten (siehe
# update_check.py und installscript/windows/setup.iss - der CI-Workflow
# vergleicht Tag und diese Nummer und bricht bei Abweichung ab)
VERSION = "1.0.0"

# Whisper
MODEL_SIZE = "small"
LANGUAGE = "de"
COMPUTE_TYPE = "int8"
# War fest auf 8 - passend fuer den 16-Kern-Entwicklungsrechner, aber auf einem
# 4-Kern-Windows-Notebook doppelte Ueberbuchung (mehr Threads als Kerne macht
# die Erkennung langsamer, nicht schneller).
CPU_THREADS = min(8, os.cpu_count() or 4)

# Audio
SAMPLE_RATE = 16000
CHANNELS = 1
BLOCKSIZE = 800  # ~50ms bei 16kHz

# Pausenerkennung / Chunking
SILENCE_THRESHOLD_RMS = 0.015
SILENCE_DURATION_MS = 700
MAX_CHUNK_DURATION_S = 18
MIN_CHUNK_DURATION_MS = 300
