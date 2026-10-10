import gc
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

from config import MODEL_SIZE, COMPUTE_TYPE, CPU_THREADS
from text_postprocess import apply_voice_commands, filter_segments


class Transcriber(threading.Thread):
    """Worker-Thread: lädt das Whisper-Modell und transkribiert danach
    fortlaufend Audio-Häppchen aus audio_q. Läuft komplett losgelöst vom
    echtzeitkritischen Audio-Callback-Thread, damit die Aufnahme nie auf die
    (deutlich langsamere) Spracherkennung warten muss.

    Ein Modellwechsel aus den Einstellungen laeuft ebenfalls hier (ueber
    control_q) statt in einem eigenen Thread: so gibt es nie zwei Modelle
    gleichzeitig im Speicher und nie zwei parallele native Thread-Pools - genau
    das hat in der Vergangenheit zu Abstuerzen gefuehrt (siehe unten)."""

    def __init__(self, audio_q: queue.Queue, result_q: queue.Queue, stop_event: threading.Event,
                 settings):
        super().__init__(daemon=True)
        self.audio_q = audio_q
        self.result_q = result_q
        self.stop_event = stop_event
        self.settings = settings
        self.control_q: queue.Queue = queue.Queue()
        self.model = None
        self.loaded_size = None

    def reload_model(self):
        """Aus dem GUI-Thread aufrufbar: laedt das in den Einstellungen
        gewaehlte Modell, sobald das aktuelle Haeppchen fertig ist."""
        self.control_q.put("reload")

    def _load(self, size: str) -> bool:
        self.result_q.put({"type": "model_loading", "model": size})
        # Altes Modell zuerst freigeben: medium und large-v3-turbo brauchen je
        # rund 1GB Arbeitsspeicher, beide zugleich koennten knapp werden.
        self.model = None
        self.loaded_size = None
        gc.collect()
        try:
            self.model = WhisperModel(
                size, device="cpu", compute_type=COMPUTE_TYPE, cpu_threads=CPU_THREADS
            )
        except Exception as exc:  # Download abgebrochen, kein Netz, Platte voll ...
            self.result_q.put({"type": "model_error", "model": size, "error": str(exc)})
            return False
        self.loaded_size = size
        self.result_q.put({"type": "model_ready", "model": size})
        return True

    def _load_with_fallback(self, previous: str | None):
        wanted = self.settings.get("model_size")
        if wanted == self.loaded_size:
            return
        if self._load(wanted):
            return
        # Lieber mit dem bisherigen (oder dem Standard-)Modell weiter als gar
        # nicht - die Einstellung wird mit zurueckgedreht, sonst stuende im
        # Dialog ein Modell, das gar nicht arbeitet.
        fallback = previous or MODEL_SIZE
        if fallback != wanted:
            self.settings.update(model_size=fallback)
            self._load(fallback)

    def run(self):
        self._load_with_fallback(previous=None)

        while not self.stop_event.is_set():
            # Mehrere schnelle Wechsel hintereinander -> nur einmal laden, und
            # zwar das zuletzt gewaehlte (steht in den Einstellungen).
            reload_requested = False
            while not self.control_q.empty():
                self.control_q.get_nowait()
                reload_requested = True
            if reload_requested:
                self._load_with_fallback(previous=self.loaded_size)

            try:
                chunk = self.audio_q.get(timeout=0.2)
            except queue.Empty:
                continue
            if self.model is None:
                continue  # kein Modell ladbar - Start ist dann ohnehin gesperrt

            # vad_filter=True (onnxruntime-basiert) bewusst deaktiviert: das startet
            # einen zweiten, unabhaengigen nativen Thread-Pool neben dem von
            # ctranslate2 und hat reproduzierbar zu Abstuerzen gefuehrt (Race
            # Condition beim Freigeben von JIT-Code, siehe Core-Dump-Analyse).
            # Die eigene Lautstaerke-basierte Pausenerkennung in audio_capture.py
            # uebernimmt die Sprache/Stille-Trennung bereits vorher.
            language = self.settings.get("language")
            hotwords = ", ".join(self.settings.get("vocabulary")) or None
            segments, _ = self.model.transcribe(
                chunk,
                language=None if language == "auto" else language,
                condition_on_previous_text=False,
                vad_filter=False,
                hotwords=hotwords,
            )
            text = apply_voice_commands(
                filter_segments(segments, hotwords=hotwords),
                punctuation=self.settings.get("punctuation_commands"),
            )
            if text is not None:
                self.result_q.put({"type": "text", "text": text})
