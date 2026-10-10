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

import audio_file
from config import MODEL_SIZE, COMPUTE_TYPE, CPU_THREADS, SAMPLE_RATE
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
        self.file_q: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
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

    def transcribe_files(self, paths: list[str], fallback_dir: str):
        """Aus dem GUI-Thread aufrufbar: Audiodateien nacheinander
        transkribieren. Ein Aufruf ist ein Auftrag; cancel_files() bricht den
        ganzen Auftrag ab, nicht nur die aktuelle Datei."""
        self.cancel_event.clear()
        self.file_q.put({"paths": list(paths), "fallback_dir": fallback_dir})

    def cancel_files(self):
        self.cancel_event.set()

    def _transcribe_array(self, audio):
        """Die einzige Stelle, die das Erkennungsmodell aufruft - live wie fuer
        Audiodateien. Liefert (Segmente, Dauer in s, eigene Woerter als
        Prompt-Text oder None); jedes Segment hat mindestens .start, .end und
        .text. Eine zweite Engine (Fahrplan M6: Parakeet) haengt sich hier ein,
        der Rest des Transcribers bleibt dann unveraendert."""
        language = self.settings.get("language")
        hotwords = ", ".join(self.settings.get("vocabulary")) or None
        # vad_filter=True (onnxruntime-basiert) bewusst deaktiviert: das startet
        # einen zweiten, unabhaengigen nativen Thread-Pool neben dem von
        # ctranslate2 und hat reproduzierbar zu Abstuerzen gefuehrt (Race
        # Condition beim Freigeben von JIT-Code, siehe Core-Dump-Analyse).
        # Live uebernimmt die eigene Lautstaerke-basierte Pausenerkennung in
        # audio_capture.py die Sprache/Stille-Trennung; bei Audiodateien
        # erfindet Whisper in langen Pausen dafuer gelegentlich Saetze - die
        # bekannten faengt filter_segments ab.
        segments, info = self.model.transcribe(
            audio,
            language=None if language == "auto" else language,
            hotwords=hotwords,
            condition_on_previous_text=False,
            vad_filter=False,
        )
        return segments, info.duration, hotwords

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
                job = self.file_q.get_nowait()
            except queue.Empty:
                pass
            else:
                self._run_file_job(job)
                continue

            try:
                chunk = self.audio_q.get(timeout=0.2)
            except queue.Empty:
                continue
            if self.model is None:
                continue  # kein Modell ladbar - Start ist dann ohnehin gesperrt

            segments, _, hotwords = self._transcribe_array(chunk)
            text = apply_voice_commands(
                filter_segments(segments, hotwords=hotwords),
                punctuation=self.settings.get("punctuation_commands"),
            )
            if text is not None:
                self.result_q.put({"type": "text", "text": text})

    def _run_file_job(self, job: dict):
        paths = job["paths"]
        for index, path in enumerate(paths, start=1):
            if self.cancel_event.is_set() or self.stop_event.is_set():
                break
            self._transcribe_file(Path(path), Path(job["fallback_dir"]), index, len(paths))
        self.result_q.put({"type": "file_job_done", "cancelled": self.cancel_event.is_set()})

    def _transcribe_file(self, path: Path, fallback_dir: Path, index: int, total: int):
        info = {"name": path.name, "index": index, "total": total}
        done = {"type": "file_done", **info, "out_path": None, "error": None, "cancelled": False}
        self.result_q.put({"type": "file_progress", **info, "phase": "decode", "percent": 0})
        if self.model is None:
            self.result_q.put({**done, "error": "kein Spracherkennungsmodell geladen"})
            return
        try:
            audio = audio_file.decode(path, SAMPLE_RATE, cancel=self.cancel_event)
            if audio is None:
                self.result_q.put({**done, "cancelled": True})
                return
            out_path = audio_file.result_path(path, fallback_dir)
        except audio_file.AudioFileError as exc:
            self.result_q.put({**done, "error": str(exc)})
            return

        self.result_q.put({"type": "file_text", "text": f"— {path.name} —"})
        punctuation = self.settings.get("punctuation_commands")
        segments, duration, hotwords = self._transcribe_array(audio)
        duration = duration or 1.0
        paragraphs = Paragraphs(lambda text: self._emit_paragraph(out_path, text))
        last_percent = 0
        try:
            for segment in segments:
                if self.cancel_event.is_set() or self.stop_event.is_set():
                    done["cancelled"] = True
                    break
                text = apply_voice_commands(
                    filter_segments([segment], hotwords=hotwords),
                    punctuation=punctuation,
                )
                if text is not None:
                    paragraphs.add(segment.start, segment.end, text)
                percent = min(99, int(segment.end / duration * 100))
                if percent != last_percent:
                    last_percent = percent
                    self.result_q.put({"type": "file_progress", **info, "phase": "transcribe",
                                       "percent": percent})
            paragraphs.flush()
            if done["cancelled"]:
                self._append(out_path, f"--- abgebrochen bei {last_percent} % ---\n")
        except OSError as exc:
            self.result_q.put({**done, "error": f"Ergebnis ließ sich nicht schreiben ({exc})"})
            return
        finally:
            del audio
            gc.collect()
        self.result_q.put({**done, "out_path": str(out_path)})

    def _emit_paragraph(self, out_path: Path, text: str):
        # Sofort schreiben statt erst am Ende: bricht das Programm bei einer
        # stundenlangen Datei ab, ist alles bis dahin Erkannte schon gesichert.
        self._append(out_path, text + "\n\n")
        self.result_q.put({"type": "file_text", "text": text})

    @staticmethod
    def _append(path: Path, text: str):
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())


class Paragraphs:
    """Fuegt Segmente einer Audiodatei zu Absaetzen zusammen. Live landet jedes
    Haeppchen in einer eigenen Zeile - eine Datei ergaebe so hunderte
    Einzeiler. Hier beginnt ein neuer Absatz nach einer Sprechpause oder wenn
    der Absatz zu lang wird (sonst erschiene bei pausenlosem Sprechen lange gar
    nichts im Fenster)."""

    PAUSE_S = 2.0
    MAX_CHARS = 700

    def __init__(self, emit):
        self._emit = emit
        self._parts: list[str] = []
        self._length = 0
        self._last_end = None

    def add(self, start: float, end: float, text: str):
        if self._parts and (start - self._last_end >= self.PAUSE_S or self._length >= self.MAX_CHARS):
            self.flush()
        self._last_end = end
        if text == "":
            self.flush()  # Segment bestand nur aus "neuer Absatz"
            return
        self._parts.append(text)
        self._length += len(text) + 1

    def flush(self):
        if self._parts:
            # Ein "neuer Absatz" mitten im Segment kommt als \n\n an - die
            # Leerzeichen drumherum vom Zusammenfuegen fallen weg.
            text = " ".join(self._parts).replace(" \n", "\n").replace("\n ", "\n")
            self._emit(text)
        self._parts = []
        self._length = 0
