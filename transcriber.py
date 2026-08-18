import os
import queue
import threading

# Muss vor dem faster_whisper-Import gesetzt werden: oneDNN waehlt auf dieser
# AMD-CPU sonst standardmaessig AVX-512-Kernel, die hier reproduzierbar zu
# Segfaults fuehren (Absturz in Xbyak::CodeGenerator::prefetcht0, siehe
# Core-Dump-Analyse). AVX2 ist auf 16 Kernen immer noch mehr als schnell genug.
os.environ.setdefault("DNNL_MAX_CPU_ISA", "AVX2")
os.environ.setdefault("ONEDNN_MAX_CPU_ISA", "AVX2")

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
