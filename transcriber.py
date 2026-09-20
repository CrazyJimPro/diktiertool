import os
import queue
import threading
from pathlib import Path

# Muss vor dem faster_whisper-Import gesetzt werden: oneDNN waehlt auf dieser
# AMD-CPU sonst standardmaessig AVX-512-Kernel, die hier reproduzierbar zu
# Segfaults fuehren (Absturz in Xbyak::CodeGenerator::prefetcht0, siehe
# Core-Dump-Analyse). AVX2 ist auf 16 Kernen immer noch mehr als schnell genug.
os.environ.setdefault("DNNL_MAX_CPU_ISA", "AVX2")
os.environ.setdefault("ONEDNN_MAX_CPU_ISA", "AVX2")

# Der Modell-Zwischenspeicher von huggingface_hub arbeitet mit Symlinks, die
# Windows nur im Entwicklermodus oder als Administrator erlaubt. Ohne beides
# funktioniert er trotzdem (er kopiert dann statt zu verlinken), warnt aber bei
# jedem Start mehrzeilig auf der Konsole. Das Verhalten ist fuer uns egal - es
# wird genau ein Modell geladen, es gibt nichts zu de-duplizieren.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Legt der Windows-Installer einen model-cache-Ordner im Projektordner an, wird
# das Modell (~500MB) dorthin geladen statt nach %USERPROFILE%\.cache\huggingface.
# Damit raeumt die Deinstallation es restlos mit weg, statt ein halbes Gigabyte
# an einer Stelle zurueckzulassen, die niemand vermutet. Unter Linux gibt es den
# Ordner nicht, dort bleibt es beim Standard-Zwischenspeicher.
_MODEL_CACHE = Path(__file__).resolve().parent / "model-cache"
if _MODEL_CACHE.is_dir():
    os.environ.setdefault("HF_HOME", str(_MODEL_CACHE))

from faster_whisper import WhisperModel

from config import MODEL_SIZE, LANGUAGE, COMPUTE_TYPE, CPU_THREADS


class Transcriber(threading.Thread):
    """Worker-Thread: lädt das Whisper-Modell einmalig und transkribiert danach
    fortlaufend Audio-Häppchen aus audio_q. Läuft komplett losgelöst vom
    echtzeitkritischen Audio-Callback-Thread, damit die Aufnahme nie auf die
    (deutlich langsamere) Spracherkennung warten muss."""

    def __init__(self, audio_q: queue.Queue, result_q: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.audio_q = audio_q
        self.result_q = result_q
        self.stop_event = stop_event
        self.model = None

    def run(self):
        self.model = WhisperModel(
            MODEL_SIZE, device="cpu", compute_type=COMPUTE_TYPE, cpu_threads=CPU_THREADS
        )
        self.result_q.put({"type": "model_ready"})

        while not self.stop_event.is_set():
            try:
                chunk = self.audio_q.get(timeout=0.2)
            except queue.Empty:
                continue

            # vad_filter=True (onnxruntime-basiert) bewusst deaktiviert: das startet
            # einen zweiten, unabhaengigen nativen Thread-Pool neben dem von
            # ctranslate2 und hat reproduzierbar zu Abstuerzen gefuehrt (Race
            # Condition beim Freigeben von JIT-Code, siehe Core-Dump-Analyse).
            # Die eigene Lautstaerke-basierte Pausenerkennung in audio_capture.py
            # uebernimmt die Sprache/Stille-Trennung bereits vorher.
            segments, _ = self.model.transcribe(
                chunk,
                language=LANGUAGE,
                condition_on_previous_text=False,
                vad_filter=False,
            )
            text = "".join(segment.text for segment in segments).strip()
            if text:
                self.result_q.put({"type": "text", "text": text})
